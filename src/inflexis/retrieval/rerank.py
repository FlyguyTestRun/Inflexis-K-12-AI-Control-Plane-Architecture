"""Reranking.

RRF produces a good *candidate* set from cheap retrievers. The reranker decides
which of those candidates actually answer the question. Keeping it behind an
interface matters: reranking is the fastest-moving part of the retrieval stack
and the platform must not be welded to one vendor (ADR-005).

Two implementations ship:

* :class:`ProviderReranker` -- delegates to a
  :class:`~inflexis.contracts.model.RerankerProvider` (production).
* :class:`HeuristicReranker` -- dependency-free, blends lexical coverage with
  authority and freshness (offline default, and a sane fallback when the
  reranking endpoint is unavailable).
"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from ..contracts.document import ScoredChunk
from ..contracts.model import RerankerProvider
from .bm25 import tokenize


class ProviderReranker:
    """Cross-encoder reranking via an injected provider.

    ``default_min_score`` is intentionally ``None``: a vendor reranker emits
    scores on its own scale, and guessing a threshold for it would silently
    mis-set the corrective gate in either direction. Deployments must calibrate
    the floor against the district gold set and pass it explicitly.
    """

    name = "provider"
    default_min_score: float | None = None

    def __init__(self, provider: RerankerProvider) -> None:
        self._provider = provider

    def rerank(
        self, query: str, candidates: Sequence[ScoredChunk], *, top_n: int
    ) -> list[ScoredChunk]:
        if not candidates:
            return []
        scores = self._provider.rerank(
            query, [c.chunk.text for c in candidates], top_n=top_n
        )
        out: list[ScoredChunk] = []
        for rank, (idx, score) in enumerate(scores[:top_n], start=1):
            original = candidates[idx]
            out.append(
                ScoredChunk(
                    chunk=original.chunk, score=score,
                    retriever=f"rerank({original.retriever})", rank=rank,
                )
            )
        return out


class HeuristicReranker:
    """Offline reranker: lexical coverage, then authority, then freshness.

    The weighting is deliberately explicit rather than learned. For district
    policy questions, a document that covers the query terms *and* is the
    current board-approved version is a better answer than one that is merely
    semantically close -- and a district can read this function and understand
    why it ranked what it ranked, which a cross-encoder cannot offer.

    Scores are anchored to lexical coverage in ``[0, 1]`` and scaled by an
    authority/freshness multiplier, so a score is roughly interpretable as
    "fraction of the question this source addresses, weighted by how much it
    should be believed". That interpretability is what lets
    :class:`~inflexis.retrieval.corrective.CorrectiveChecker` apply an absolute
    relevance threshold at all.
    """

    name = "heuristic"
    #: Calibrated against the synthetic district: genuine matches score ~1.2-1.5
    #: while incidental single-token overlap scores <0.45. Re-tune per district
    #: against its gold set -- see docs/evaluation/gold-set-spec.md.
    default_min_score: float = 0.5

    def __init__(
        self, *, coverage_weight: float = 1.0, authority_weight: float = 0.35,
        freshness_weight: float = 0.15,
    ) -> None:
        self.coverage_weight = coverage_weight
        self.authority_weight = authority_weight
        self.freshness_weight = freshness_weight

    def rerank(
        self, query: str, candidates: Sequence[ScoredChunk], *, top_n: int
    ) -> list[ScoredChunk]:
        q_terms = set(tokenize(query))
        if not q_terms:
            return list(candidates[:top_n])
        today = date.today()
        rescored: list[tuple[ScoredChunk, float]] = []
        for cand in candidates:
            chunk = cand.chunk
            terms = set(tokenize(chunk.text + " " + chunk.title))
            coverage = len(q_terms & terms) / len(q_terms)
            # AuthorityLevel is 1 (highest) .. 10 (lowest); map to 1.0 .. 0.0.
            authority = (10 - chunk.authority_level.value) / 9
            freshness = 1.0 if chunk.is_current(today) else 0.0
            # Authority and freshness *amplify* relevance; they never create
            # it. An additive form would give an irrelevant but authoritative
            # document a high score floor, which lets nonsense queries clear
            # the corrective gate. Multiplying by coverage means a document
            # that does not address the question scores zero no matter how
            # authoritative it is.
            score = (
                self.coverage_weight
                * coverage
                * (
                    1.0
                    + self.authority_weight * authority
                    + self.freshness_weight * freshness
                )
            )
            rescored.append((cand, score))
        rescored.sort(key=lambda x: x[1], reverse=True)
        return [
            ScoredChunk(
                chunk=c.chunk, score=s, retriever=f"rerank({c.retriever})",
                rank=i + 1,
            )
            for i, (c, s) in enumerate(rescored[:top_n])
        ]
