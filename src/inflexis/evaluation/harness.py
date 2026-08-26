"""The evaluation harness.

Two properties distinguish this from a "does the chatbot sound good" review:

1. It measures **refusal correctness**. A case whose right answer is "I cannot
   answer that" fails if the system answers, even if the answer is fluent.
2. It measures **leakage** as a hard gate. Retrieval quality metrics are scores
   to improve; a leaked forbidden source is a release blocker, and the report
   says so rather than averaging it into an aggregate.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from ..contracts.classification import AuthorityLevel
from ..contracts.evaluation import (
    CaseResult,
    ExpectedBehaviour,
    GoldCase,
    RetrievalMetrics,
    SecurityMetrics,
)
from ..contracts.identity import Principal, Role
from ..contracts.retrieval import CorrectiveAction

#: Maps a corrective action onto the behaviour the gold set describes.
_ACTION_TO_BEHAVIOUR = {
    CorrectiveAction.GENERATE: ExpectedBehaviour.ANSWER,
    CorrectiveAction.REFUSE: ExpectedBehaviour.REFUSE,
    CorrectiveAction.CLARIFY: ExpectedBehaviour.CLARIFY,
    CorrectiveAction.ESCALATE: ExpectedBehaviour.ESCALATE,
    CorrectiveAction.REWRITE_QUERY: ExpectedBehaviour.CLARIFY,
    CorrectiveAction.BROADEN_SOURCES: ExpectedBehaviour.CLARIFY,
}


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    results: tuple[CaseResult, ...]
    retrieval: RetrievalMetrics
    security: SecurityMetrics
    by_behaviour: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.results else 0.0

    @property
    def release_blocked(self) -> bool:
        """Security failures block release regardless of the pass rate."""
        return not self.security.is_clean

    def summary(self) -> str:
        lines = [
            f"cases: {self.passed}/{self.total} passed ({self.pass_rate:.0%})",
            f"recall@k: {self.retrieval.recall_at_k:.2f}  "
            f"precision@k: {self.retrieval.precision_at_k:.2f}  "
            f"MRR: {self.retrieval.mrr:.2f}  nDCG: {self.retrieval.ndcg:.2f}",
            f"authority hit rate: {self.retrieval.authority_hit_rate:.2f}  "
            f"freshness hit rate: {self.retrieval.freshness_hit_rate:.2f}",
        ]
        for behaviour, (ok, count) in sorted(self.by_behaviour.items()):
            lines.append(f"  {behaviour}: {ok}/{count}")
        if self.release_blocked:
            lines.append(
                f"RELEASE BLOCKED -- unauthorized retrievals: "
                f"{self.security.unauthorized_retrievals}, "
                f"cross-tenant leaks: {self.security.cross_tenant_leaks}"
            )
        return "\n".join(lines)


class EvaluationHarness:
    """Runs a gold set against an authorized retrieval pipeline."""

    def __init__(
        self,
        run_query: Callable[[Principal, GoldCase], object],
        principals_by_role: dict[Role, Principal],
    ) -> None:
        self._run = run_query
        self._principals = principals_by_role

    def run(self, cases: Sequence[GoldCase]) -> EvaluationReport:
        results: list[CaseResult] = []
        recalls, precisions, rrs, ndcgs = [], [], [], []
        authority_hits, authority_total = 0, 0
        fresh_hits, fresh_total = 0, 0
        unauthorized = 0
        cross_tenant = 0
        by_behaviour: dict[str, list[int]] = {}

        for case in cases:
            principal = self._principals.get(case.as_role)
            if principal is None:
                results.append(
                    CaseResult(
                        case_id=case.case_id,
                        passed=False,
                        observed_behaviour=ExpectedBehaviour.REFUSE,
                        failure_reason=f"no principal configured for role {case.as_role}",
                    )
                )
                continue

            context = self._run(principal, case)
            observed = _ACTION_TO_BEHAVIOUR.get(
                context.verdict.action, ExpectedBehaviour.REFUSE
            )
            retrieved = tuple(e.chunk.chunk_id for e in context.evidence)

            leaked = tuple(sorted(set(retrieved) & case.forbidden_sources))
            if leaked:
                unauthorized += 1
            cross_tenant += sum(
                1
                for e in context.evidence
                if case.tenant_id and e.chunk.tenant_id != case.tenant_id
            )

            behaviour_ok = observed is case.expected_behaviour
            failure = ""
            if not behaviour_ok:
                failure = (
                    f"expected {case.expected_behaviour.value}, "
                    f"observed {observed.value} ({context.verdict.reason})"
                )
            if leaked:
                failure = f"leaked forbidden sources: {list(leaked)}"

            citation_ok = (
                bool(context.citations)
                if (case.citation_required and observed is ExpectedBehaviour.ANSWER)
                else True
            )
            if not citation_ok:
                failure = failure or "answer produced without citations"

            expected_ok = True
            if case.expected_sources:
                expected_ok = bool(set(retrieved) & case.expected_sources)
                if not expected_ok and not failure:
                    failure = (
                        f"expected one of {sorted(case.expected_sources)}, "
                        f"retrieved {list(retrieved)}"
                    )

            passed = behaviour_ok and not leaked and citation_ok and expected_ok
            results.append(
                CaseResult(
                    case_id=case.case_id,
                    passed=passed,
                    observed_behaviour=observed,
                    retrieved_chunk_ids=retrieved,
                    leaked_chunk_ids=leaked,
                    failure_reason=failure,
                )
            )

            bucket = by_behaviour.setdefault(case.expected_behaviour.value, [0, 0])
            bucket[1] += 1
            if passed:
                bucket[0] += 1

            # Ranking metrics only make sense where a target set exists.
            if case.expected_sources:
                recalls.append(
                    len(set(retrieved) & case.expected_sources)
                    / len(case.expected_sources)
                )
                precisions.append(
                    len(set(retrieved) & case.expected_sources) / len(retrieved)
                    if retrieved
                    else 0.0
                )
                rrs.append(_reciprocal_rank(retrieved, case.expected_sources))
                ndcgs.append(_ndcg(retrieved, case.expected_sources))

            if case.authority_requirement is not None and context.evidence:
                authority_total += 1
                if any(
                    e.chunk.authority_level.value <= case.authority_requirement.value
                    for e in context.evidence
                ):
                    authority_hits += 1
            if case.freshness_required and context.evidence:
                fresh_total += 1
                if all(e.chunk.is_current() for e in context.evidence):
                    fresh_hits += 1

        return EvaluationReport(
            results=tuple(results),
            retrieval=RetrievalMetrics(
                recall_at_k=_mean(recalls),
                precision_at_k=_mean(precisions),
                mrr=_mean(rrs),
                ndcg=_mean(ndcgs),
                hit_rate=_mean([1.0 if r > 0 else 0.0 for r in rrs]),
                authority_hit_rate=(
                    authority_hits / authority_total if authority_total else 0.0
                ),
                freshness_hit_rate=(
                    fresh_hits / fresh_total if fresh_total else 0.0
                ),
            ),
            security=SecurityMetrics(
                cross_tenant_leaks=cross_tenant,
                unauthorized_retrievals=unauthorized,
            ),
            by_behaviour={k: (v[0], v[1]) for k, v in by_behaviour.items()},
        )


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _reciprocal_rank(retrieved: Sequence[str], expected: frozenset[str]) -> float:
    for i, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in expected:
            return 1.0 / i
    return 0.0


def _ndcg(retrieved: Sequence[str], expected: frozenset[str]) -> float:
    dcg = sum(
        1.0 / math.log2(i + 1)
        for i, chunk_id in enumerate(retrieved, start=1)
        if chunk_id in expected
    )
    ideal = sum(
        1.0 / math.log2(i + 1)
        for i in range(1, min(len(expected), max(len(retrieved), 1)) + 1)
    )
    return dcg / ideal if ideal else 0.0


def load_gold_set(path: str | Path) -> list[GoldCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = []
    for row in payload["cases"]:
        authority = row.get("authority_requirement")
        cases.append(
            GoldCase(
                case_id=row["case_id"],
                query=row["query"],
                as_role=Role(row["as_role"]),
                expected_behaviour=ExpectedBehaviour(row["expected_behaviour"]),
                expected_sources=frozenset(row.get("expected_sources", [])),
                forbidden_sources=frozenset(row.get("forbidden_sources", [])),
                expected_answer_contains=tuple(
                    row.get("expected_answer_contains", [])
                ),
                authority_requirement=(
                    AuthorityLevel(authority) if authority else None
                ),
                freshness_required=row.get("freshness_required", True),
                citation_required=row.get("citation_required", True),
                risk_level=row.get("risk_level", "low"),
                tenant_id=row.get("tenant_id", payload.get("tenant_id", "")),
                notes=row.get("notes", ""),
            )
        )
    return cases
