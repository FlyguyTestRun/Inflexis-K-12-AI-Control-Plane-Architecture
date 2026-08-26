"""Dense vector retrieval.

The embedding provider is injected. The default
:class:`HashingEmbeddingProvider` is a deterministic, dependency-free stand-in
so that tests, CI, and the synthetic district run without a model endpoint.

It is NOT a semantic model. It exists so the *pipeline* can be exercised and
its security properties tested offline. Production deployments inject a real
:class:`~inflexis.contracts.model.EmbeddingProvider`; nothing else changes.
"""

from __future__ import annotations

import hashlib
import math
from typing import Sequence

from ..contracts.authz import AuthorizedQuery
from ..contracts.document import Chunk, ScoredChunk
from ..contracts.model import EmbeddingProvider
from ..contracts.retrieval import RetrievalResult, RetrievalStrategy
from .bm25 import tokenize
from .index import InMemoryIndex


class HashingEmbeddingProvider:
    """Deterministic bag-of-words hashing embedding. Offline test double.

    Produces stable vectors with meaningful cosine similarity for lexical
    overlap, which is enough to verify fusion, filtering, and ranking
    plumbing -- and honest about being no substitute for a trained model.
    """

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dimensions
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else vec


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class VectorRetriever:
    """Semantic retrieval over the chunk store."""

    name = "vector"

    def __init__(
        self, index: InMemoryIndex, embedder: EmbeddingProvider | None = None
    ) -> None:
        self._index = index
        self._embedder = embedder or HashingEmbeddingProvider()
        self._cache: dict[str, list[float]] = {}

    def _vector_for(self, chunk: Chunk) -> list[float]:
        # Keyed by content hash so a re-indexed but unchanged chunk reuses its
        # embedding, and a tampered chunk does not.
        key = chunk.provenance.content_hash
        if key not in self._cache:
            self._cache[key] = self._embedder.embed([chunk.text])[0]
        return self._cache[key]

    def retrieve(self, query: AuthorizedQuery) -> RetrievalResult:
        corpus = list(self._index.scan(query.filter))
        if not corpus:
            return RetrievalResult(
                results=(), strategy=RetrievalStrategy.VECTOR,
                query_text=query.text, diagnostics={"corpus_size": 0},
            )
        q_vec = self._embedder.embed([query.text])[0]
        scored = sorted(
            ((c, cosine(q_vec, self._vector_for(c))) for c in corpus),
            key=lambda x: x[1],
            reverse=True,
        )
        results = tuple(
            ScoredChunk(chunk=c, score=s, retriever=self.name, rank=i + 1)
            for i, (c, s) in enumerate(scored[: query.top_k])
            if s > 0
        )
        return RetrievalResult(
            results=results,
            strategy=RetrievalStrategy.VECTOR,
            query_text=query.text,
            diagnostics={"corpus_size": len(corpus)},
        )
