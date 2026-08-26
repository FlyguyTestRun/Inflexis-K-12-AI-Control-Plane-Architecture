"""BM25 lexical retrieval.

District knowledge is full of exact terminology that dense embeddings blur:
``EIC(LOCAL)``, ``TEC 25.085``, ``DAEP``, ``FAPE``, ``IEP``, ``504``, ``HB 149``,
board policy codes, version numbers, dates, employee ids. A teacher asking
"what does EIC(LOCAL) say about tardies" needs the document that literally
contains that token, and a vector search will happily return three
semantically-similar attendance policies that are not it.

Hence BM25 as a first-class half of the default pipeline, not a fallback.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from ..contracts.authz import AuthorizedQuery
from ..contracts.document import Chunk, ScoredChunk
from ..contracts.retrieval import RetrievalResult, RetrievalStrategy
from .index import InMemoryIndex

# Keeps policy codes such as EIC(LOCAL), TEC 25.085, and 504 intact rather than
# shattering them into meaningless fragments.
_TOKEN = re.compile(r"[A-Za-z0-9]+(?:\.[0-9]+)*(?:\([A-Za-z]+\))?")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


class BM25Retriever:
    """Okapi BM25 over the chunk store.

    ``k1`` and ``b`` use the conventional defaults. They are exposed because
    district corpora vary in chunk-length uniformity, and ``b`` (length
    normalisation) in particular is worth tuning against the district gold set.
    """

    name = "bm25"

    def __init__(
        self, index: InMemoryIndex, *, k1: float = 1.5, b: float = 0.75
    ) -> None:
        self._index = index
        self.k1 = k1
        self.b = b

    def retrieve(self, query: AuthorizedQuery) -> RetrievalResult:
        # The filter is applied during the scan; unauthorized chunks are never
        # scored and never enter the candidate pool.
        corpus: list[Chunk] = list(self._index.scan(query.filter))
        scored = self._score(query.text, corpus)
        results = tuple(
            ScoredChunk(chunk=c, score=s, retriever=self.name, rank=i + 1)
            for i, (c, s) in enumerate(scored[: query.top_k])
            if s > 0
        )
        return RetrievalResult(
            results=results,
            strategy=RetrievalStrategy.LEXICAL,
            query_text=query.text,
            diagnostics={"corpus_size": len(corpus)},
        )

    def _score(
        self, query_text: str, corpus: Sequence[Chunk]
    ) -> list[tuple[Chunk, float]]:
        if not corpus:
            return []
        docs = [tokenize(c.text + " " + c.title) for c in corpus]
        lengths = [len(d) for d in docs]
        avgdl = sum(lengths) / len(lengths) if lengths else 0.0
        n_docs = len(docs)

        df: Counter[str] = Counter()
        for doc in docs:
            df.update(set(doc))

        q_terms = tokenize(query_text)
        scores: list[tuple[Chunk, float]] = []
        for chunk, doc, dl in zip(corpus, docs, lengths, strict=True):
            tf = Counter(doc)
            score = 0.0
            for term in q_terms:
                freq = tf.get(term, 0)
                if freq == 0:
                    continue
                # Standard BM25 IDF with the +0.5 smoothing that keeps the
                # value positive for terms appearing in most documents.
                idf = math.log(
                    1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5)
                )
                denom = freq + self.k1 * (
                    1 - self.b + self.b * (dl / avgdl if avgdl else 1.0)
                )
                score += idf * (freq * (self.k1 + 1)) / denom
            scores.append((chunk, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
