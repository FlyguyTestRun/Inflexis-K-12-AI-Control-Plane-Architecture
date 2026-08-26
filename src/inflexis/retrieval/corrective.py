"""Corrective RAG: the quality gate between retrieval and generation.

The single most damaging failure mode for a district assistant is a confident
answer built on thin, stale, or contradictory evidence. Corrective RAG treats
"we do not have good enough evidence" as a *first-class, correct outcome*
rather than an error to be papered over.

The checker never invents evidence and never lowers its own bar to produce an
answer. When evidence is insufficient it returns the corrective action the
orchestrator should take: rewrite, broaden, clarify, escalate, or refuse.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from ..contracts.classification import (
    DEFAULT_AUTHORITATIVE_THRESHOLD,
    AuthorityLevel,
)
from ..contracts.document import ScoredChunk
from ..contracts.retrieval import (
    CorrectiveAction,
    Sufficiency,
    SufficiencyVerdict,
)


class CorrectiveChecker:
    """Evaluates a candidate evidence set before generation.

    ``min_score`` is interpreted on *the reranker's* score scale. It defaults to
    the value calibrated for :class:`~inflexis.retrieval.rerank.HeuristicReranker`;
    a deployment using a different reranker must pass its own calibrated floor,
    which :class:`~inflexis.retrieval.pipeline.HybridRetrievalPipeline` does
    automatically when the reranker advertises ``default_min_score``.

    Setting ``min_score`` to 0 disables the relevance gate entirely: every
    candidate with any positive score is treated as relevant, so a query that
    merely shares a common word with the corpus will produce a confident
    answer. That is the failure this class exists to prevent.

    ``require_authority`` defaults to **off**, and that is deliberate. The
    authority *ranking* always influences reranking, but an authority *gate* is
    a use-case property, not a platform-wide one. "What does board policy say
    about class rank" should demand a board-policy-or-higher source; "what is
    the bell schedule at my campus" is authoritatively answered by a campus
    document that sits well below the policy threshold. Enabling the gate
    globally would classify most legitimate district content as untrustworthy
    and drive the assistant to refuse routine operational questions.

    The intent/risk router turns the gate on for policy and compliance use
    cases; see ``docs/retrieval/retrieval-architecture.md``.
    """

    def __init__(
        self,
        *,
        min_results: int = 1,
        min_score: float = 0.5,
        authority_threshold: AuthorityLevel = DEFAULT_AUTHORITATIVE_THRESHOLD,
        require_authority: bool = False,
        max_rewrites: int = 1,
    ) -> None:
        self.min_results = min_results
        self.min_score = min_score
        self.authority_threshold = authority_threshold
        self.require_authority = require_authority
        self.max_rewrites = max_rewrites

    def check(
        self,
        candidates: Sequence[ScoredChunk],
        *,
        attempt: int = 0,
        as_of: date | None = None,
    ) -> SufficiencyVerdict:
        as_of = as_of or date.today()

        if not candidates:
            # Nothing authorized and relevant exists. One rewrite is worth
            # trying (the user may have used district jargon we do not index),
            # but after that, refusing is the correct answer -- not guessing.
            if attempt < self.max_rewrites:
                return SufficiencyVerdict(
                    Sufficiency.EMPTY,
                    CorrectiveAction.REWRITE_QUERY,
                    "no authorized evidence matched; retrying with a rewritten query",
                )
            return SufficiencyVerdict(
                Sufficiency.EMPTY,
                CorrectiveAction.REFUSE,
                "no authorized evidence available for this question",
            )

        strong = [c for c in candidates if c.score > self.min_score]
        if len(strong) < self.min_results:
            action = (
                CorrectiveAction.REWRITE_QUERY
                if attempt < self.max_rewrites
                else CorrectiveAction.REFUSE
            )
            return SufficiencyVerdict(
                Sufficiency.INSUFFICIENT_RELEVANCE,
                action,
                f"only {len(strong)} candidate(s) above relevance threshold",
            )

        current = [c for c in strong if c.chunk.is_current(as_of)]
        if not current:
            # Evidence exists but every piece is expired or superseded.
            # Answering from it would state repealed policy as current.
            return SufficiencyVerdict(
                Sufficiency.STALE,
                CorrectiveAction.ESCALATE,
                "all matching evidence is expired or superseded; a human should "
                "confirm the current version",
            )

        if self.require_authority:
            authoritative = [
                c
                for c in current
                if c.chunk.authority_level.value <= self.authority_threshold.value
            ]
            if not authoritative:
                return SufficiencyVerdict(
                    Sufficiency.INSUFFICIENT_AUTHORITY,
                    CorrectiveAction.BROADEN_SOURCES
                    if attempt < self.max_rewrites
                    else CorrectiveAction.ESCALATE,
                    "no source meets the authority threshold "
                    f"({self.authority_threshold.name}) for this question",
                )
            current = authoritative

        conflict = self._detect_conflict(current)
        if conflict:
            # Do not silently pick a winner. Surface the disagreement.
            return SufficiencyVerdict(
                Sufficiency.CONFLICTING,
                CorrectiveAction.ESCALATE,
                "sources of equal authority disagree; escalating rather than "
                "choosing between them",
                conflicting_chunk_ids=conflict,
            )

        return SufficiencyVerdict(
            Sufficiency.SUFFICIENT,
            CorrectiveAction.GENERATE,
            f"{len(current)} authorized, current, authoritative source(s)",
        )

    def _detect_conflict(
        self, candidates: Sequence[ScoredChunk]
    ) -> tuple[str, ...]:
        """Flag same-authority sources that supersede one another.

        Conservative by design: it detects the structurally checkable case
        (two versions of the same document family at equal authority, both
        active) rather than attempting semantic contradiction detection, which
        would be unreliable and would produce false confidence.
        """
        by_family: dict[tuple[str, int], list[ScoredChunk]] = {}
        for cand in candidates:
            key = (cand.chunk.document_id.split("#")[0], cand.chunk.authority_level.value)
            by_family.setdefault(key, []).append(cand)

        conflicting: list[str] = []
        for group in by_family.values():
            versions = {c.chunk.version for c in group}
            if len(versions) > 1:
                conflicting.extend(c.chunk.chunk_id for c in group)
        return tuple(conflicting)
