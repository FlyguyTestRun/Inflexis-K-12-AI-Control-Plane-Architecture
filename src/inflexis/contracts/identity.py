"""Identity, tenancy, and the caller principal.

Every operation in the control plane is performed *by a principal, inside a
tenant*. There is no ambient authority and no "system" caller that skips
authorization; background jobs carry a service principal with its own scoped
roles (see ``docs/security/trust-boundaries.md``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType


class Role(StrEnum):
    """Platform roles.

    Districts map their own identity-provider groups onto these roles through
    tenant configuration; the platform never consumes raw IdP group names in
    authorization logic, because group naming differs per district and would
    otherwise leak into policy code.
    """

    PUBLIC = "public"
    STUDENT = "student"
    TEACHER = "teacher"
    COUNSELOR = "counselor"
    PRINCIPAL = "principal"
    IT_ADMIN = "it_admin"
    HR = "hr"
    SUPERINTENDENT = "superintendent"
    AI_RISK_OFFICER = "ai_risk_officer"
    PLATFORM_ADMIN = "platform_admin"
    SERVICE = "service"


class Permission(StrEnum):
    """Fine-grained entitlements, checked in addition to roles.

    Roles answer "who is this person"; permissions answer "what has this person
    been entitled to do". Keeping them separate lets a district grant a narrow
    capability without promoting someone into a broad role.
    """

    RETRIEVE = "retrieve"
    RETRIEVE_PERSONNEL = "retrieve.personnel"
    RETRIEVE_STUDENT = "retrieve.student"
    RETRIEVE_SPED = "retrieve.sped"
    RETRIEVE_LEGAL = "retrieve.legal"
    TOOL_INVOKE_READ = "tool.invoke.read"
    TOOL_INVOKE_WRITE = "tool.invoke.write"
    GOVERNANCE_READ = "governance.read"
    GOVERNANCE_WRITE = "governance.write"
    GOVERNANCE_APPROVE = "governance.approve"
    AUDIT_READ = "audit.read"
    INGEST = "ingest"


@dataclass(frozen=True, slots=True)
class Tenant:
    """A district. The unit of isolation.

    ``tenant_id`` is the hard isolation boundary: it is applied as a mandatory
    predicate on every retrieval, every audit query, and every tool invocation.
    No configuration, role, or policy can widen a query across tenants.
    """

    tenant_id: str
    district_id: str
    display_name: str
    #: Trust domains this district has actually provisioned. A domain that is
    #: not provisioned is not retrievable even for a principal who holds the
    #: matching permission.
    enabled_trust_domains: frozenset[str] = field(default_factory=frozenset)
    #: District-specific overrides for configurable authority levels 4-10.
    authority_overrides: Mapping[str, int] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __post_init__(self) -> None:
        if not self.tenant_id:
            raise ValueError("tenant_id is required; there is no default tenant")


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller.

    Constructed only by the authentication layer from a verified token. The
    retrieval and tool layers treat this as trusted input; everything else
    (prompt text, document content, tool output) is untrusted.
    """

    subject_id: str
    tenant_id: str
    roles: frozenset[Role]
    permissions: frozenset[Permission] = field(default_factory=frozenset)
    #: ABAC attributes: campus, department, employment status, etc. Used for
    #: attribute-based narrowing such as "this principal sees only Campus 01".
    attributes: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    #: Set when the principal is a non-human service identity.
    is_service: bool = False

    def __post_init__(self) -> None:
        if not self.subject_id or not self.tenant_id:
            raise ValueError("principal requires subject_id and tenant_id")
        if not self.roles:
            raise ValueError(
                "principal requires at least one role; "
                "an unroled principal must be rejected at authentication"
            )

    def has_role(self, *roles: Role) -> bool:
        return any(r in self.roles for r in roles)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

    @property
    def campus_id(self) -> str | None:
        return self.attributes.get("campus_id")

    @property
    def department_id(self) -> str | None:
        return self.attributes.get("department_id")


#: The anonymous public caller. Still a principal, still tenant-scoped, still
#: subject to the same authorization path -- it simply carries the narrowest
#: possible entitlements.
def anonymous_principal(tenant_id: str) -> Principal:
    return Principal(
        subject_id="anonymous",
        tenant_id=tenant_id,
        roles=frozenset({Role.PUBLIC}),
        permissions=frozenset({Permission.RETRIEVE}),
    )
