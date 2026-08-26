"""Authorization contracts: the retrieval filter and the authorized query.

ADR-003 requires that authorization happen *before* retrieval, not after. The
usual way that requirement decays is that someone adds a new retriever, forgets
the filter, and nothing complains until a teacher sees an HR file.

This module makes the requirement structural. A retriever accepts an
:class:`AuthorizedQuery`, and an ``AuthorizedQuery`` cannot be constructed by
calling code -- only a policy decision point holding the module-private grant
token can mint one. A retriever therefore *cannot* be called without proof that
a policy decision was made, and the filter travels with the query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Protocol

from .classification import AuthorityLevel, DocumentStatus, TrustDomain
from .document import Chunk
from .identity import Principal

# Module-private capability token. Holding a reference to this object is the
# only way to construct an AuthorizedQuery. It is deliberately not exported in
# __all__ and must never be re-exported from a public module.
_GRANT = object()


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """The record of an authorization decision. Always audited."""

    effect: Effect
    principal_id: str
    tenant_id: str
    action: str
    reason: str
    #: Policy rules that fired, for explainability and for evidence.
    matched_rules: tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.effect is Effect.ALLOW


@dataclass(frozen=True, slots=True)
class RetrievalFilter:
    """The mandatory predicate set applied to every retrieval backend.

    Every field here narrows the searchable space. There is no field that
    widens it. A backend adapter translates this into its native query language
    (SQL ``WHERE``, Azure AI Search ``$filter``, etc.) and must apply *all* of
    it; :func:`enforce_filter` provides a defence-in-depth re-check in process.
    """

    tenant_id: str
    allowed_trust_domains: frozenset[TrustDomain]
    principal: Principal
    allowed_statuses: frozenset[DocumentStatus] = field(
        default_factory=lambda: frozenset({DocumentStatus.ACTIVE})
    )
    #: When set, only chunks at or above this authority are retrievable.
    min_authority: AuthorityLevel | None = None
    #: When set, restricts to a campus. Derived from ABAC attributes.
    campus_scope: frozenset[str] | None = None
    department_scope: frozenset[str] | None = None
    as_of: date | None = None

    def permits(self, chunk: Chunk) -> bool:
        """The in-process re-check. Order matters: cheapest, hardest first."""
        if chunk.tenant_id != self.tenant_id:
            return False
        if chunk.trust_domain not in self.allowed_trust_domains:
            return False
        if chunk.status not in self.allowed_statuses:
            return False
        if not chunk.is_current(self.as_of):
            return False
        if self.min_authority is not None and (
            chunk.authority_level.value > self.min_authority.value
        ):
            return False
        if self.campus_scope is not None and chunk.campus_id is not None:
            if chunk.campus_id not in self.campus_scope:
                return False
        if self.department_scope is not None and chunk.department_id is not None:
            if chunk.department_id not in self.department_scope:
                return False
        return chunk.acl.permits(self.principal)


@dataclass(frozen=True, slots=True)
class AuthorizedQuery:
    """A query that has passed authorization, carrying its filter.

    Construct only via a :class:`PolicyDecisionPoint`. Direct construction
    raises, which is what makes ADR-003 enforceable by the type system rather
    than by code review.
    """

    text: str
    filter: RetrievalFilter
    decision: PolicyDecision
    top_k: int = 20
    _grant: object = None

    def __post_init__(self) -> None:
        if self._grant is not _GRANT:
            raise PermissionError(
                "AuthorizedQuery cannot be constructed directly. Obtain one "
                "from a PolicyDecisionPoint.authorize_retrieval() call so that "
                "authorization provably precedes retrieval (ADR-003)."
            )
        if not self.decision.allowed:
            raise PermissionError("cannot build an AuthorizedQuery from a DENY")

    @property
    def principal(self) -> Principal:
        return self.filter.principal


def _mint(
    text: str, filt: RetrievalFilter, decision: PolicyDecision, top_k: int
) -> AuthorizedQuery:
    """Internal factory. Only policy decision points may call this."""
    return AuthorizedQuery(
        text=text, filter=filt, decision=decision, top_k=top_k, _grant=_GRANT
    )


def enforce_filter(
    chunks: list[Chunk], filt: RetrievalFilter
) -> tuple[list[Chunk], list[str]]:
    """Defence in depth: drop anything the backend should not have returned.

    Returns the surviving chunks and the ids of anything dropped. A non-empty
    drop list means a backend adapter failed to apply the filter and is a
    security incident, not a warning -- callers are expected to audit it.
    """
    kept, dropped = [], []
    for chunk in chunks:
        if filt.permits(chunk):
            kept.append(chunk)
        else:
            dropped.append(chunk.chunk_id)
    return kept, dropped


class PolicyDecisionPoint(Protocol):
    """The interface every policy engine implementation must satisfy."""

    def authorize_retrieval(
        self, principal: Principal, query: str, *, top_k: int = 20,
        use_case_id: str | None = None,
    ) -> AuthorizedQuery:
        """Return an authorized query or raise ``PermissionError``."""
        ...

    def authorize_tool(
        self, principal: Principal, tool_name: str, arguments: dict
    ) -> PolicyDecision:
        ...
