"""The starting tool catalogue.

Phase 3 begins with read-only tools only. The write tools are declared here as
*descriptors without implementations* so that their risk posture is reviewable
and their approval requirements are visible before anyone builds them --
see ``docs/implementation/phase-1-plan.md``.
"""

from __future__ import annotations

from ..contracts.identity import Permission, Role
from ..contracts.tools import RiskLevel, ToolDescriptor

_STAFF = frozenset(
    {
        Role.TEACHER,
        Role.COUNSELOR,
        Role.PRINCIPAL,
        Role.IT_ADMIN,
        Role.HR,
        Role.SUPERINTENDENT,
        Role.AI_RISK_OFFICER,
    }
)

POLICY_SEARCH = ToolDescriptor(
    name="policy_search",
    description="Search board policy, administrative regulations, and district procedures.",
    risk_level=RiskLevel.LOW,
    read_only=True,
    required_roles=_STAFF | {Role.PUBLIC, Role.STUDENT},
    required_permissions=frozenset({Permission.RETRIEVE}),
    data_domains=frozenset({"A_public", "B_district_internal"}),
)

DISTRICT_DOC_SEARCH = ToolDescriptor(
    name="district_documentation_search",
    description="Search approved district handbooks and departmental documentation.",
    risk_level=RiskLevel.LOW,
    read_only=True,
    required_roles=_STAFF,
    required_permissions=frozenset({Permission.RETRIEVE}),
    data_domains=frozenset({"B_district_internal"}),
)

IT_KNOWLEDGE_SEARCH = ToolDescriptor(
    name="it_knowledge_search",
    description="Search IT standard operating procedures and infrastructure documentation.",
    risk_level=RiskLevel.LOW,
    read_only=True,
    required_roles=frozenset({Role.IT_ADMIN, Role.SUPERINTENDENT}),
    required_permissions=frozenset({Permission.RETRIEVE, Permission.TOOL_INVOKE_READ}),
    data_domains=frozenset({"B_district_internal"}),
)

APPROVED_WEB_SEARCH = ToolDescriptor(
    name="approved_web_search",
    description="Search an allow-listed set of external sources (TEA, statute, vendor docs).",
    risk_level=RiskLevel.MEDIUM,
    read_only=True,
    required_roles=_STAFF,
    required_permissions=frozenset({Permission.TOOL_INVOKE_READ}),
    data_domains=frozenset({"A_public"}),
    credential_scope="none",
    # Web content is attacker-controllable and is the primary prompt-injection
    # vector for an agent. Treated as MEDIUM rather than LOW for that reason.
)

SQL_ANALYTICS = ToolDescriptor(
    name="sql_analytics",
    description=(
        "Run allow-listed, parameterised aggregate queries against the "
        "reporting warehouse."
    ),
    risk_level=RiskLevel.MEDIUM,
    read_only=True,
    required_roles=frozenset({Role.PRINCIPAL, Role.SUPERINTENDENT, Role.IT_ADMIN}),
    required_permissions=frozenset({Permission.TOOL_INVOKE_READ}),
    data_domains=frozenset({"B_district_internal"}),
    credential_scope="reporting_readonly",
)

READ_ONLY_TOOLS: tuple[ToolDescriptor, ...] = (
    POLICY_SEARCH,
    DISTRICT_DOC_SEARCH,
    IT_KNOWLEDGE_SEARCH,
    APPROVED_WEB_SEARCH,
    SQL_ANALYTICS,
)

# --- Declared, deliberately not implemented (Phase 3.5) -------------------

CREATE_TICKET = ToolDescriptor(
    name="create_ticket",
    description="Create a service desk ticket on behalf of a staff member.",
    risk_level=RiskLevel.MEDIUM,
    read_only=False,
    required_roles=_STAFF,
    required_permissions=frozenset({Permission.TOOL_INVOKE_WRITE}),
    credential_scope="servicedesk_create_only",
    requires_human_approval=False,
    reversible=True,
    rollback_supported=True,
)

SEND_EMAIL = ToolDescriptor(
    name="send_email",
    description="Send email from a district account.",
    risk_level=RiskLevel.HIGH,
    read_only=False,
    required_roles=frozenset({Role.SUPERINTENDENT, Role.IT_ADMIN}),
    required_permissions=frozenset({Permission.TOOL_INVOKE_WRITE}),
    credential_scope="mail_send_scoped",
    requires_human_approval=True,
    # An email cannot be unsent. Saying otherwise in a descriptor would be a
    # lie the approval workflow would then rely on.
    reversible=False,
    rollback_supported=False,
)

PROPOSED_WRITE_TOOLS: tuple[ToolDescriptor, ...] = (CREATE_TICKET, SEND_EMAIL)
