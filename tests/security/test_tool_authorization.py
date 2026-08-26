"""Tool authorization tests (docs/architecture.md s37).

Covers: unauthorized tool cannot execute, unauthorized write is blocked, and
an unregistered tool name is denied rather than improvised.
"""

import pytest

from inflexis.contracts.identity import Permission, Role
from inflexis.contracts.tools import RiskLevel, ToolDescriptor, ToolResult
from inflexis.tools import ToolAuthorizationError, ToolRegistry
from inflexis.tools.catalog import (
    IT_KNOWLEDGE_SEARCH,
    POLICY_SEARCH,
    SEND_EMAIL,
    CREATE_TICKET,
)


class _StubTool:
    """Minimal tool that records whether its body ever ran."""

    def __init__(self, descriptor: ToolDescriptor) -> None:
        self.descriptor = descriptor
        self.invoked = False

    def invoke(self, invocation, principal) -> ToolResult:
        self.invoked = True
        return ToolResult(tool_name=self.descriptor.name, ok=True, output="ran")


@pytest.fixture
def registry(acme_engine, audit):
    reg = ToolRegistry(acme_engine, audit_sink=audit)
    tools = {}
    for descriptor in (POLICY_SEARCH, IT_KNOWLEDGE_SEARCH, CREATE_TICKET, SEND_EMAIL):
        stub = _StubTool(descriptor)
        tools[descriptor.name] = stub
        reg.register(stub)
    reg._stubs = tools  # test handle
    return reg


class TestUnauthorizedToolIsBlocked:
    def test_teacher_cannot_invoke_it_only_tool(self, registry, people, audit):
        with pytest.raises(ToolAuthorizationError):
            registry.invoke(people["teacher"], "it_knowledge_search")
        assert not registry._stubs["it_knowledge_search"].invoked, (
            "tool body executed despite denial"
        )
        assert audit.security_events(), "denial was not audited"

    def test_it_admin_can_invoke_it_tool(self, registry, people):
        result = registry.invoke(people["it_admin"], "it_knowledge_search")
        assert result.ok

    def test_unregistered_tool_is_denied(self, registry, people):
        with pytest.raises(ToolAuthorizationError, match="not registered"):
            registry.invoke(people["teacher"], "delete_student_record")

    def test_cross_tenant_tool_invocation_denied(self, registry, people):
        with pytest.raises(ToolAuthorizationError, match="cross-tenant"):
            registry.invoke(people["bravo_teacher"], "policy_search")


class TestWriteOperationsBlocked:
    def test_write_tool_denied_without_write_permission(self, registry, people):
        """No synthetic principal holds TOOL_INVOKE_WRITE -- by design."""
        with pytest.raises(ToolAuthorizationError, match="tool.invoke.write"):
            registry.invoke(people["teacher"], "create_ticket")
        assert not registry._stubs["create_ticket"].invoked

    def test_high_risk_tool_requires_human_approval_even_for_superintendent(
        self, registry, people
    ):
        import dataclasses

        empowered = dataclasses.replace(
            people["superintendent"],
            permissions=people["superintendent"].permissions
            | {Permission.TOOL_INVOKE_WRITE},
        )
        with pytest.raises(ToolAuthorizationError, match="human approval"):
            registry.invoke(empowered, "send_email")
        assert not registry._stubs["send_email"].invoked


class TestAvailableToolsAreScoped:
    def test_planner_sees_only_invokable_tools(self, registry, people):
        teacher_tools = {d.name for d in registry.available_to(people["teacher"])}
        it_tools = {d.name for d in registry.available_to(people["it_admin"])}
        assert "it_knowledge_search" not in teacher_tools
        assert "it_knowledge_search" in it_tools
        # No write tool is offered to anyone at this phase.
        assert "send_email" not in teacher_tools | it_tools
        assert "create_ticket" not in teacher_tools | it_tools


class TestDescriptorInvariants:
    def test_cannot_declare_high_risk_write_without_approval(self):
        with pytest.raises(ValueError, match="human approval"):
            ToolDescriptor(
                name="bad_tool",
                description="writes without approval",
                risk_level=RiskLevel.HIGH,
                read_only=False,
                required_roles=frozenset({Role.IT_ADMIN}),
                required_permissions=frozenset({Permission.TOOL_INVOKE_WRITE}),
                requires_human_approval=False,
                rollback_supported=True,
            )

    def test_cannot_disable_audit(self):
        with pytest.raises(ValueError, match="audit is not optional"):
            ToolDescriptor(
                name="silent_tool",
                description="no audit",
                risk_level=RiskLevel.LOW,
                read_only=True,
                required_roles=frozenset({Role.IT_ADMIN}),
                required_permissions=frozenset(),
                audit_required=False,
            )

    def test_cannot_declare_roleless_tool(self):
        with pytest.raises(ValueError, match="no required_roles"):
            ToolDescriptor(
                name="open_tool",
                description="anyone",
                risk_level=RiskLevel.LOW,
                read_only=True,
                required_roles=frozenset(),
                required_permissions=frozenset(),
            )
