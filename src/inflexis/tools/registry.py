"""The tool registry and the gateway that guards it.

Two rules make this component worth having:

1. A tool that is not registered cannot be invoked. An agent that hallucinates
   a tool name gets a denial, not an accident.
2. Authorization is checked by the gateway on *every* invocation, using the
   caller's principal -- never using the agent's identity, and never using
   anything the model said about who the caller is.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..contracts.audit import AuditEvent, AuditEventType, AuditSink, Severity
from ..contracts.authz import Effect, PolicyDecision
from ..contracts.identity import Principal
from ..contracts.tools import Tool, ToolDescriptor, ToolInvocation, ToolResult


class ToolAuthorizationError(PermissionError):
    """Raised when a tool invocation is denied. Always audited."""

    def __init__(self, decision: PolicyDecision) -> None:
        super().__init__(f"tool denied: {decision.reason}")
        self.decision = decision


class ToolRegistry:
    """Registry + authorizing gateway for all tool invocations."""

    def __init__(
        self,
        policy_engine,
        *,
        audit_sink: AuditSink | None = None,
        tools: Iterable[Tool] = (),
    ) -> None:
        self._policy = policy_engine
        self._audit = audit_sink
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        descriptor = tool.descriptor
        if descriptor.name in self._tools:
            raise ValueError(f"tool {descriptor.name!r} is already registered")
        self._tools[descriptor.name] = tool

    @property
    def descriptors(self) -> Mapping[str, ToolDescriptor]:
        return {name: t.descriptor for name, t in self._tools.items()}

    def available_to(self, principal: Principal) -> list[ToolDescriptor]:
        """Tools this principal may actually invoke.

        An agent planner is shown only this list. Advertising tools the caller
        cannot use invites the model to plan around capabilities it will then
        be denied, which produces confusing failures and tempts retry loops.
        """
        allowed = []
        for tool in self._tools.values():
            decision = self._policy.authorize_tool(principal, tool.descriptor, {})
            if decision.allowed:
                allowed.append(tool.descriptor)
        return allowed

    def invoke(
        self, principal: Principal, name: str, arguments: Mapping | None = None
    ) -> ToolResult:
        arguments = dict(arguments or {})
        tool = self._tools.get(name)

        if tool is None:
            decision = PolicyDecision(
                effect=Effect.DENY,
                principal_id=principal.subject_id,
                tenant_id=principal.tenant_id,
                action=f"tool:{name}",
                reason=f"tool {name!r} is not registered",
            )
            self._audit_denial(principal, name, decision)
            raise ToolAuthorizationError(decision)

        decision = self._policy.authorize_tool(principal, tool.descriptor, arguments)
        if not decision.allowed:
            self._audit_denial(principal, name, decision)
            raise ToolAuthorizationError(decision)

        result = tool.invoke(
            ToolInvocation(
                tool_name=name,
                arguments=arguments,
                principal_id=principal.subject_id,
                tenant_id=principal.tenant_id,
            ),
            principal,
        )
        self._emit(
            AuditEvent(
                event_type=AuditEventType.TOOL_INVOCATION,
                tenant_id=principal.tenant_id,
                principal_id=principal.subject_id,
                action=f"tool:{name}",
                outcome="ok" if result.ok else "error",
                detail={"read_only": tool.descriptor.read_only},
            )
        )
        return result

    def _audit_denial(
        self, principal: Principal, name: str, decision: PolicyDecision
    ) -> None:
        self._emit(
            AuditEvent(
                event_type=AuditEventType.TOOL_DENIED,
                tenant_id=principal.tenant_id,
                principal_id=principal.subject_id,
                action=f"tool:{name}",
                outcome="denied",
                severity=Severity.SECURITY,
                detail={"reason": decision.reason},
            )
        )

    def _emit(self, event: AuditEvent) -> None:
        if self._audit is not None:
            self._audit.emit(event)
