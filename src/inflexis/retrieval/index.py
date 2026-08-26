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

from typing import Iterable, Iterator

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
