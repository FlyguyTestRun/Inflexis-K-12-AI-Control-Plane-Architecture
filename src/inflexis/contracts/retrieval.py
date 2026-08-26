"""Retrieval contracts (Plane 4).

Five retrieval strategies sit behind *one* orchestration abstraction. They are
not five products; they are implementations of :class:`Retriever` selected by
the intent/risk router.

Every retriever takes an :class:`~inflexis.contracts.authz.AuthorizedQuery`,
which cannot exist without a prior policy decision. That is the whole point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Sequence

from .authz import AuthorizedQuery
from .document import Chunk, ScoredChunk


class RetrievalStrategy(str, Enum):
    HYBRID = "hybrid"
    LEXICAL = "lexical"
    VECTOR = "vector"
    GRAPH = "graph"
    AGENTIC = "agentic"
    MULTIMODAL = "multimodal"


class Sufficiency(str, Enum):
    """The corrective-RAG verdict on a candidate evidence set."""

    SUFFICIENT = "sufficient"
    INSUFFICIENT_RELEVANCE = "insufficient_relevance"
    INSUFFICIENT_AUTHORITY = "insufficient_authority"
    STALE = "stale"
    CONFLICTING = "conflicting"
    EMPTY = "empty"
    AMBIGUOUS_QUERY = "ambiguous_query"

    @property
    def can_generate(self) -> bool:
        return self is Sufficiency.SUFFICIENT


class CorrectiveAction(str, Enum):
    GENERATE = "generate"
    REWRITE_QUERY = "rewrite_query"
    BROADEN_SOURCES = "broaden_sources"
    CLARIFY = "clarify"
    ESCALATE = "escalate"
    REFUSE = "refuse"


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """What a retriever returns, with enough detail to evaluate and audit it."""

    results: tuple[ScoredChunk, ...]
    strategy: RetrievalStrategy
    #: Chunks the backend returned but the in-process filter rejected. Any
    #: non-empty value here is a backend filter bug and a security event.
    filtered_out: tuple[str, ...] = ()
    query_text: str = ""
    diagnostics: dict = field(default_factory=dict)

    @property
    def chunks(self) -> list[Chunk]:
        return [r.chunk for r in self.results]

    def top(self, n: int) -> "RetrievalResult":
        return RetrievalResult(
            results=self.results[:n],
            strategy=self.strategy,
            filtered_out=self.filtered_out,
            query_text=self.query_text,
            diagnostics=self.diagnostics,
        )


@dataclass(frozen=True, slots=True)
class SufficiencyVerdict:
    """Output of the corrective check."""

    sufficiency: Sufficiency
    action: CorrectiveAction
    reason: str
    #: Populated when CONFLICTING: the chunk ids that disagree.
    conflicting_chunk_ids: tuple[str, ...] = ()


class Retriever(Protocol):
    """One retrieval strategy.

    Implementations MUST apply ``query.filter`` inside the backend query and
    MUST NOT return content the filter excludes. The pipeline re-checks in
    process, but a retriever that relies on that re-check is broken: it means
    unauthorized content was read out of the datastore.
    """

    name: str

    def retrieve(self, query: AuthorizedQuery) -> RetrievalResult: ...


class FusionStrategy(Protocol):
    """Combines several ranked lists into one."""

    def fuse(
        self, result_sets: Sequence[RetrievalResult], *, top_k: int
    ) -> list[ScoredChunk]: ...


class Reranker(Protocol):
    """Reorders fused candidates by true relevance to the query."""

    name: str

    def rerank(
        self, query: str, candidates: Sequence[ScoredChunk], *, top_n: int
    ) -> list[ScoredChunk]: ...
