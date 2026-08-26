"""Tool and action contracts (Plane 6).

Every tool declares its full security posture up front. A tool that has not
declared these fields cannot be registered, which means an agent can never be
handed a capability whose blast radius nobody wrote down.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from .identity import Permission, Principal, Role


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """The governance record for one tool. Mirrors ``schemas/tool.schema.json``."""

    name: str
    description: str
    risk_level: RiskLevel
    read_only: bool
    required_roles: frozenset[Role]
    required_permissions: frozenset[Permission]
    tenant_scope: str = "single"
    data_domains: frozenset[str] = field(default_factory=frozenset)
    credential_scope: str = "none"
    requires_human_approval: bool = False
    audit_required: bool = True
    reversible: bool = True
    rollback_supported: bool = False

    def __post_init__(self) -> None:
        if not self.required_roles:
            raise ValueError(
                f"tool {self.name!r} declares no required_roles; a tool callable "
                "by any role is not a governed tool"
            )
        if not self.audit_required:
            raise ValueError(
                f"tool {self.name!r} disables audit; audit is not optional"
            )
        if not self.read_only and not self.requires_human_approval:
            if self.risk_level in (RiskLevel.HIGH, RiskLevel.PROHIBITED):
                raise ValueError(
                    f"tool {self.name!r} is a high-risk write tool without human "
                    "approval; see docs/architecture.md s30"
                )
        if not self.read_only and not self.rollback_supported and self.reversible:
            raise ValueError(
                f"tool {self.name!r} claims reversible but supports no rollback"
            )
        if self.tenant_scope not in {"single", "none"}:
            raise ValueError(
                f"tool {self.name!r}: tenant_scope must be 'single' or 'none'; "
                "cross-tenant tools are not permitted"
            )


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    tool_name: str
    arguments: Mapping[str, Any]
    principal_id: str
    tenant_id: str
    approved_by: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_name: str
    ok: bool
    output: Any = None
    error: str = ""
    #: Tool output is untrusted input to the model. Adapters must set this so
    #: the orchestrator can wrap it in an untrusted-content envelope.
    untrusted: bool = True


class Tool(Protocol):
    descriptor: ToolDescriptor

    def invoke(self, invocation: ToolInvocation, principal: Principal) -> ToolResult:
        ...


ToolFn = Callable[[ToolInvocation, Principal], ToolResult]
