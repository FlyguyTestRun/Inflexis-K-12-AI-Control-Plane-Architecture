"""The policy decision point.

This is the only component permitted to mint an
:class:`~inflexis.contracts.authz.AuthorizedQuery`. Everything downstream --
every retriever, every reranker, the generator -- can therefore assume that a
policy decision was made, and can read the filter that decision produced.

Design notes
------------
* The engine is **deny by default**. A role with no grant gets no trust domains
  and every retrieval fails closed.
* Trust-domain grants are *intersected* with the tenant's provisioned domains,
  so a misconfigured role in one district cannot reach a domain that district
  never enabled.
* ABAC narrowing (campus, department) is applied as a filter predicate, not as
  a post-hoc check.
* The engine never consults the user's prompt text when deciding entitlements.
  Prompt content is untrusted; letting it influence authorization is precisely
  the prompt-injection privilege-escalation path (OWASP LLM01/LLM06).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Mapping

from ..contracts import authz as _authz
from ..contracts.authz import (
    AuthorizedQuery,
    Effect,
    PolicyDecision,
    RetrievalFilter,
)
from ..contracts.classification import (
    RESTRICTED_BY_DEFAULT,
    AuthorityLevel,
    DocumentStatus,
    TrustDomain,
)
from ..contracts.identity import Permission, Principal, Role, Tenant
from ..contracts.tools import ToolDescriptor


@dataclass(frozen=True, slots=True)
class TrustDomainGrant:
    """What one role may reach, and under what extra conditions."""

    domains: frozenset[TrustDomain]
    #: Permissions the principal must ALSO hold for this grant to apply.
    requires_permissions: frozenset[Permission] = field(default_factory=frozenset)
    #: When True, the grant is narrowed to the principal's own campus.
    campus_scoped: bool = False


#: Platform default role grants. Districts override these in tenant config;
#: the defaults are intentionally tight, because the failure mode of a tight
#: default is a support ticket and the failure mode of a loose one is a
#: FERPA incident.
DEFAULT_ROLE_GRANTS: Mapping[Role, TrustDomainGrant] = {
    Role.PUBLIC: TrustDomainGrant(domains=frozenset({TrustDomain.PUBLIC})),
    Role.STUDENT: TrustDomainGrant(
        domains=frozenset({TrustDomain.PUBLIC}),
    ),
    Role.TEACHER: TrustDomainGrant(
        domains=frozenset({TrustDomain.PUBLIC, TrustDomain.DISTRICT_INTERNAL}),
        campus_scoped=True,
    ),
    Role.COUNSELOR: TrustDomainGrant(
        domains=frozenset(
            {
                TrustDomain.PUBLIC,
                TrustDomain.DISTRICT_INTERNAL,
                TrustDomain.STUDENT_CONFIDENTIAL,
            }
        ),
        requires_permissions=frozenset({Permission.RETRIEVE_STUDENT}),
        campus_scoped=True,
    ),
    Role.PRINCIPAL: TrustDomainGrant(
        domains=frozenset(
            {
                TrustDomain.PUBLIC,
                TrustDomain.DISTRICT_INTERNAL,
                TrustDomain.STUDENT_CONFIDENTIAL,
            }
        ),
        requires_permissions=frozenset({Permission.RETRIEVE_STUDENT}),
        campus_scoped=True,
    ),
    Role.HR: TrustDomainGrant(
        domains=frozenset(
            {
                TrustDomain.PUBLIC,
                TrustDomain.DISTRICT_INTERNAL,
                TrustDomain.PERSONNEL,
            }
        ),
        requires_permissions=frozenset({Permission.RETRIEVE_PERSONNEL}),
    ),
    Role.IT_ADMIN: TrustDomainGrant(
        domains=frozenset({TrustDomain.PUBLIC, TrustDomain.DISTRICT_INTERNAL}),
    ),
    Role.SUPERINTENDENT: TrustDomainGrant(
        domains=frozenset(
            {
                TrustDomain.PUBLIC,
                TrustDomain.DISTRICT_INTERNAL,
                TrustDomain.PERSONNEL,
                TrustDomain.STUDENT_CONFIDENTIAL,
            }
        ),
        requires_permissions=frozenset(
            {Permission.RETRIEVE_PERSONNEL, Permission.RETRIEVE_STUDENT}
        ),
    ),
    Role.AI_RISK_OFFICER: TrustDomainGrant(
        domains=frozenset({TrustDomain.PUBLIC, TrustDomain.DISTRICT_INTERNAL}),
    ),
    Role.PLATFORM_ADMIN: TrustDomainGrant(
        domains=frozenset({TrustDomain.PUBLIC, TrustDomain.DISTRICT_INTERNAL}),
    ),
    Role.SERVICE: TrustDomainGrant(domains=frozenset()),
}


class PolicyEngine:
    """Reference policy decision point.

    Note what is deliberately absent: there is no ``allow_all``, no
    ``bypass_for_admin``, and no way for a caller to supply its own filter.
    A platform admin is an administrator of the *platform*, not a reader of
    every district's student records.
    """

    def __init__(
        self,
        tenant: Tenant,
        *,
        role_grants: Mapping[Role, TrustDomainGrant] | None = None,
        restricted_domains: frozenset[TrustDomain] = RESTRICTED_BY_DEFAULT,
    ) -> None:
        self._tenant = tenant
        self._grants = dict(role_grants or DEFAULT_ROLE_GRANTS)
        self._restricted = restricted_domains

    # -- retrieval ----------------------------------------------------------

    def allowed_domains(self, principal: Principal) -> frozenset[TrustDomain]:
        """Union of grants for the principal's roles, then narrowed."""
        granted: set[TrustDomain] = set()
        for role in principal.roles:
            grant = self._grants.get(role)
            if grant is None:
                continue
            if not grant.requires_permissions <= principal.permissions:
                # The role would allow it, but the principal lacks the explicit
                # entitlement. Role alone is never sufficient for sensitive
                # domains.
                granted |= grant.domains - {
                    TrustDomain.PERSONNEL,
                    TrustDomain.STUDENT_CONFIDENTIAL,
                    TrustDomain.HIGHLY_SENSITIVE,
                }
                continue
            granted |= grant.domains

        # Domains restricted by default are never reachable through a
        # general-purpose grant; they require a dedicated approved use case.
        granted -= self._restricted

        # Intersect with what this district actually provisioned.
        if self._tenant.enabled_trust_domains:
            enabled = {
                d for d in TrustDomain if d.value in self._tenant.enabled_trust_domains
            }
            granted &= enabled
        return frozenset(granted)

    def _campus_scope(self, principal: Principal) -> frozenset[str] | None:
        scoped = any(
            self._grants.get(r) and self._grants[r].campus_scoped
            for r in principal.roles
        )
        unscoped = any(
            self._grants.get(r) and not self._grants[r].campus_scoped
            for r in principal.roles
        )
        if scoped and not unscoped and principal.campus_id:
            return frozenset({principal.campus_id})
        return None

    def authorize_retrieval(
        self,
        principal: Principal,
        query: str,
        *,
        top_k: int = 20,
        use_case_id: str | None = None,
        min_authority: AuthorityLevel | None = None,
        as_of: date | None = None,
    ) -> AuthorizedQuery:
        """Return an authorized query, or raise ``PermissionError``."""
        if principal.tenant_id != self._tenant.tenant_id:
            raise PermissionError(
                f"principal {principal.subject_id!r} belongs to tenant "
                f"{principal.tenant_id!r} and cannot query tenant "
                f"{self._tenant.tenant_id!r}"
            )
        if not principal.has_permission(Permission.RETRIEVE):
            raise PermissionError(
                f"principal {principal.subject_id!r} lacks the RETRIEVE permission"
            )

        domains = self.allowed_domains(principal)
        if not domains:
            raise PermissionError(
                f"principal {principal.subject_id!r} has no readable trust domain "
                "in this tenant; refusing to run an unscoped query"
            )

        filt = RetrievalFilter(
            tenant_id=self._tenant.tenant_id,
            allowed_trust_domains=domains,
            principal=principal,
            allowed_statuses=frozenset({DocumentStatus.ACTIVE}),
            min_authority=min_authority,
            campus_scope=self._campus_scope(principal),
            as_of=as_of,
        )
        decision = PolicyDecision(
            effect=Effect.ALLOW,
            principal_id=principal.subject_id,
            tenant_id=self._tenant.tenant_id,
            action="retrieve",
            reason=f"granted domains: {sorted(d.value for d in domains)}",
            matched_rules=tuple(sorted(r.value for r in principal.roles)),
        )
        return _authz._mint(query, filt, decision, top_k)

    # -- tools --------------------------------------------------------------

    def authorize_tool(
        self, principal: Principal, tool: ToolDescriptor, arguments: dict | None = None
    ) -> PolicyDecision:
        """Least-privilege tool authorization. Deny by default."""

        def deny(reason: str) -> PolicyDecision:
            return PolicyDecision(
                effect=Effect.DENY,
                principal_id=principal.subject_id,
                tenant_id=self._tenant.tenant_id,
                action=f"tool:{tool.name}",
                reason=reason,
            )

        if principal.tenant_id != self._tenant.tenant_id:
            return deny("cross-tenant tool invocation")
        if not principal.has_role(*tool.required_roles):
            return deny(
                f"principal lacks any of the required roles "
                f"{sorted(r.value for r in tool.required_roles)}"
            )
        if not tool.required_permissions <= principal.permissions:
            missing = sorted(
                p.value for p in tool.required_permissions - principal.permissions
            )
            return deny(f"principal lacks required permissions {missing}")
        if not tool.read_only and not principal.has_permission(
            Permission.TOOL_INVOKE_WRITE
        ):
            return deny("write tool requires the TOOL_INVOKE_WRITE permission")
        if tool.requires_human_approval:
            return deny(
                "tool requires human approval; route through the approval "
                "workflow rather than invoking directly"
            )
        return PolicyDecision(
            effect=Effect.ALLOW,
            principal_id=principal.subject_id,
            tenant_id=self._tenant.tenant_id,
            action=f"tool:{tool.name}",
            reason="role, permission, and approval requirements satisfied",
            matched_rules=tuple(sorted(r.value for r in tool.required_roles)),
        )
