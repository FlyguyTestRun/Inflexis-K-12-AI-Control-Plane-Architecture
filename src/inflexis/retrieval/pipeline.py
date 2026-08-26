"""The governed hybrid retrieval pipeline.

This is the concrete realisation of the architecture diagram: authorization,
then parallel lexical + semantic retrieval, then RRF, then reranking, then the
in-process filter re-check, then the corrective gate, then -- only if the gate
says yes -- generation.

The pipeline stops at "authorized, sufficient evidence + a corrective verdict".
Generation is deliberately a separate step behind the model gateway so that the
retrieval half can be tested, evaluated, and audited without a model endpoint.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

from ..contracts.audit import AuditEvent, AuditEventType, AuditSink, Severity
from ..contracts.authz import AuthorizedQuery, enforce_filter
from ..contracts.document import ScoredChunk
from ..contracts.retrieval import (
    CorrectiveAction,
    Reranker,
    RetrievalResult,
    RetrievalStrategy,
    Retriever,
    SufficiencyVerdict,
)
from .corrective import CorrectiveChecker
from .fusion import ReciprocalRankFusion


@dataclass(frozen=True, slots=True)
class GroundedContext:
    """The output of the pipeline: evidence cleared for generation.

    If ``verdict.action`` is not ``GENERATE``, ``evidence`` is empty and the
    orchestrator must take the corrective action instead of answering. There is
    no path that returns evidence alongside a refusal verdict, because that
    combination invites a caller to answer anyway.
    """

    verdict: SufficiencyVerdict
    evidence: tuple[ScoredChunk, ...] = ()
    query_text: str = ""
    citations: tuple[str, ...] = ()
    diagnostics: dict = field(default_factory=dict)

    @property
    def may_generate(self) -> bool:
        return self.verdict.action is CorrectiveAction.GENERATE


class HybridRetrievalPipeline:
    """BM25 + vector -> RRF -> rerank -> re-filter -> corrective check."""

    def __init__(
        self,
        retrievers: Sequence[Retriever],
        reranker: Reranker,
        *,
        fusion: ReciprocalRankFusion | None = None,
        corrective: CorrectiveChecker | None = None,
        audit_sink: AuditSink | None = None,
        candidate_pool: int = 50,
        final_n: int = 8,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
    ) -> None:
        if not retrievers:
            raise ValueError("a retrieval pipeline needs at least one retriever")
        self._retrievers = list(retrievers)
        self._reranker = reranker
        self._fusion = fusion or ReciprocalRankFusion()
        # The relevance floor is a property of the reranker's score scale, so
        # take it from the reranker rather than assuming a platform-wide value.
        if corrective is not None:
            self._corrective = corrective
        else:
            floor = getattr(reranker, "default_min_score", None)
            self._corrective = (
                CorrectiveChecker() if floor is None else CorrectiveChecker(min_score=floor)
            )
        self._audit = audit_sink
        self.candidate_pool = candidate_pool
        self.final_n = final_n
        self.strategy = strategy

    def run(
        self,
        query: AuthorizedQuery,
        *,
        attempt: int = 0,
        as_of: date | None = None,
        ai_system_id: str | None = None,
    ) -> GroundedContext:
        started = time.perf_counter()

        result_sets: list[RetrievalResult] = [
            retriever.retrieve(query) for retriever in self._retrievers
        ]

        fused = self._fusion.fuse(result_sets, top_k=self.candidate_pool)
        reranked = self._reranker.rerank(
            query.text, fused, top_n=self.final_n
        )

        # Defence in depth. A backend adapter that failed to apply the filter
        # is a security incident, not a retrieval quality problem -- so it is
        # audited at SECURITY severity and the offending chunks are dropped.
        surviving_chunks, dropped = enforce_filter(
            [c.chunk for c in reranked], query.filter
        )
        surviving_ids = {c.chunk_id for c in surviving_chunks}
        evidence = tuple(c for c in reranked if c.chunk.chunk_id in surviving_ids)

        if dropped:
            self._emit(
                AuditEvent(
                    event_type=AuditEventType.FILTER_VIOLATION,
                    tenant_id=query.filter.tenant_id,
                    principal_id=query.principal.subject_id,
                    action="retrieve",
                    outcome="filtered",
                    severity=Severity.SECURITY,
                    ai_system_id=ai_system_id,
                    evidence_refs=tuple(dropped),
                    detail={
                        "message": "retriever returned chunks the filter rejected",
                        "retrievers": [r.name for r in self._retrievers],
                    },
                )
            )

        verdict = self._corrective.check(evidence, attempt=attempt, as_of=as_of)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if verdict.action is not CorrectiveAction.GENERATE:
            self._emit(
                AuditEvent(
                    event_type=AuditEventType.REFUSAL
                    if verdict.action is CorrectiveAction.REFUSE
                    else AuditEventType.RETRIEVAL,
                    tenant_id=query.filter.tenant_id,
                    principal_id=query.principal.subject_id,
                    action="retrieve",
                    outcome=verdict.action.value,
                    severity=Severity.NOTICE,
                    ai_system_id=ai_system_id,
                    latency_ms=elapsed_ms,
                    detail={
                        "sufficiency": verdict.sufficiency.value,
                        "reason": verdict.reason,
                    },
                )
            )
            return GroundedContext(
                verdict=verdict,
                query_text=query.text,
                diagnostics=self._diagnostics(result_sets, fused, elapsed_ms),
            )

        citations = tuple(
            c.chunk.provenance.citation(c.chunk.title) for c in evidence
        )
        self._emit(
            AuditEvent(
                event_type=AuditEventType.RETRIEVAL,
                tenant_id=query.filter.tenant_id,
                principal_id=query.principal.subject_id,
                action="retrieve",
                outcome="sufficient",
                ai_system_id=ai_system_id,
                evidence_refs=tuple(c.chunk.chunk_id for c in evidence),
                latency_ms=elapsed_ms,
                detail={"strategy": self.strategy.value},
            )
        )
        return GroundedContext(
            verdict=verdict,
            evidence=evidence,
            query_text=query.text,
            citations=citations,
            diagnostics=self._diagnostics(result_sets, fused, elapsed_ms),
        )

    def _diagnostics(
        self,
        result_sets: Sequence[RetrievalResult],
        fused: Sequence[ScoredChunk],
        elapsed_ms: int,
    ) -> dict:
        return {
            "per_retriever": {
                rs.strategy.value: len(rs.results) for rs in result_sets
            },
            "fused_candidates": len(fused),
            "latency_ms": elapsed_ms,
        }

    def _emit(self, event: AuditEvent) -> None:
        if self._audit is not None:
            self._audit.emit(event)
