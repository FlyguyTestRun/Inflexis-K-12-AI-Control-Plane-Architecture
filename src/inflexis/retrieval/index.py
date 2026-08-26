"""Reference in-memory index.

This is a *reference implementation* used for tests, the synthetic district,
and local development without cloud dependencies. Production deployments swap
in an adapter over Azure AI Search or PostgreSQL (see ADR-005); the contract
they must satisfy is the one exercised here.

The security-critical property demonstrated by this class is that the filter is
applied *during* the scan, not after. An adapter that fetches first and filters
later would still pass the pipeline's re-check while having already read
unauthorized rows out of the datastore -- which is exactly the failure ADR-003
exists to prevent.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Iterator, Mapping

from ..contracts.authz import RetrievalFilter
from ..contracts.document import Chunk


class InMemoryIndex:
    """Tenant-partitioned chunk store."""

    def __init__(self) -> None:
        # Partitioned by tenant so that a missing filter predicate cannot
        # silently scan another district's content.
        self._by_tenant: dict[str, list[Chunk]] = {}

    def add(self, chunk: Chunk) -> None:
        chunk.validate()
        self._by_tenant.setdefault(chunk.tenant_id, []).append(chunk)

    def add_all(self, chunks: Iterable[Chunk]) -> None:
        for chunk in chunks:
            self.add(chunk)

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_tenant.values())

    def scan(self, filt: RetrievalFilter) -> Iterator[Chunk]:
        """Yield only chunks the filter permits, within the filter's tenant."""
        for chunk in self._by_tenant.get(filt.tenant_id, ()):
            if filt.permits(chunk):
                yield chunk

    def scan_unfiltered(self, tenant_id: str) -> Iterator[Chunk]:
        """Ingestion/administration only. Never call from a retrieval path."""
        yield from self._by_tenant.get(tenant_id, ())

    def statistics(self, tenant_id: str) -> "CorpusStatistics":
        """Term statistics for one tenant, used for relevance weighting."""
        from .bm25 import tokenize

        chunks = self._by_tenant.get(tenant_id, ())
        df: Counter[str] = Counter()
        for chunk in chunks:
            df.update(set(tokenize(chunk.text + " " + chunk.title)))
        return CorpusStatistics(n_docs=len(chunks), document_frequency=dict(df))


@dataclass(frozen=True, slots=True)
class CorpusStatistics:
    """Per-tenant term statistics used to weight relevance by informativeness.

    Deliberately tenant-scoped. Document frequencies computed across tenants
    would let one district's corpus composition influence -- and in principle be
    inferred from -- another district's ranking, which is a side channel through
    a component nobody thinks of as security-relevant.
    """

    n_docs: int
    document_frequency: Mapping[str, int]

    def weight(self, term: str) -> float:
        """Informativeness of a term. Rare terms carry the signal.

        A term in nearly every document (``the``, ``district``, ``policy``)
        approaches zero weight, so a query that matches only such terms cannot
        clear the corrective relevance floor. That is the whole point: without
        it, "what is the district policy on interplanetary field trips" scores
        as a confident hit against unrelated board policy.
        """
        df = self.document_frequency.get(term, 0)
        return math.log(1 + self.n_docs / (df + 1))
