"""Reciprocal Rank Fusion.

BM25 scores and cosine similarities are not on a common scale and are not
comparable. Adding or averaging them is a category error that silently lets
whichever retriever happens to produce larger numbers dominate the blend.

RRF sidesteps the problem by discarding magnitudes and fusing *ranks*:

    score(d) = sum over result lists of  1 / (k + rank(d))

``k`` (conventionally 60) damps the influence of the very top ranks so that a
document found at rank 3 by both retrievers can outrank one found at rank 1 by
only one. Agreement between retrievers is the signal RRF rewards.
"""

from __future__ import annotations

from typing import Sequence

from ..contracts.document import ScoredChunk
from ..contracts.retrieval import RetrievalResult

DEFAULT_K = 60


class ReciprocalRankFusion:
    """Rank-based fusion of any number of ranked result lists."""

    name = "rrf"

    def __init__(self, k: int = DEFAULT_K, weights: dict[str, float] | None = None):
        if k <= 0:
            raise ValueError("RRF k must be positive")
        self.k = k
        # Optional per-retriever weighting. Districts whose corpus is
        # code-heavy may weight lexical higher; the default is unweighted
        # because unweighted RRF is the honest starting point before the
        # district gold set says otherwise.
        self.weights = weights or {}

    def fuse(
        self, result_sets: Sequence[RetrievalResult], *, top_k: int
    ) -> list[ScoredChunk]:
        accumulated: dict[str, float] = {}
        best_chunk: dict[str, ScoredChunk] = {}
        contributors: dict[str, set[str]] = {}

        for result_set in result_sets:
            for rank, scored in enumerate(result_set.results, start=1):
                cid = scored.chunk.chunk_id
                weight = self.weights.get(scored.retriever, 1.0)
                accumulated[cid] = accumulated.get(cid, 0.0) + weight / (
                    self.k + rank
                )
                contributors.setdefault(cid, set()).add(scored.retriever)
                # Keep a representative ScoredChunk for the chunk payload.
                if cid not in best_chunk or scored.rank < best_chunk[cid].rank:
                    best_chunk[cid] = scored

        fused = [
            ScoredChunk(
                chunk=best_chunk[cid].chunk,
                score=score,
                retriever="+".join(sorted(contributors[cid])),
            )
            for cid, score in accumulated.items()
        ]
        fused.sort(key=lambda s: s.score, reverse=True)
        return [
            ScoredChunk(
                chunk=s.chunk, score=s.score, retriever=s.retriever, rank=i + 1
            )
            for i, s in enumerate(fused[:top_k])
        ]
