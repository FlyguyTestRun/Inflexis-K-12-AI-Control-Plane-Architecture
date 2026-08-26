"""Audit and provenance contracts.

An audit record must be sufficient, on its own, to reconstruct *who asked what,
what the platform decided, what evidence it used, and what it said back*. That
is the evidentiary standard a district needs when a parent, a board member, or
counsel asks how an answer was produced.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence


class AuditEventType(str, Enum):
    AUTHZ_DECISION = "authz.decision"
    RETRIEVAL = "retrieval"
    FILTER_VIOLATION = "retrieval.filter_violation"
    GENERATION = "generation"
    REFUSAL = "refusal"
    TOOL_INVOCATION = "tool.invocation"
    TOOL_DENIED = "tool.denied"
    HUMAN_APPROVAL = "human.approval"
    INGESTION = "ingestion"
    GOVERNANCE_CHANGE = "governance.change"
    POLICY_EXCEPTION = "policy.exception"
    INCIDENT = "incident"


class Severity(str, Enum):
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    SECURITY = "security"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """One immutable audit record.

    Audit records never contain retrieved document *text* -- only identifiers,
    hashes, and decisions. Copying confidential content into the audit log
    creates a second, usually less well protected, copy of the data.
    """

    event_type: AuditEventType
    tenant_id: str
    principal_id: str
    action: str
    outcome: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    severity: Severity = Severity.INFO
    ai_system_id: str | None = None
    use_case_id: str | None = None
    #: Chunk ids and content hashes -- never chunk text.
    evidence_refs: tuple[str, ...] = ()
    model_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    detail: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.principal_id:
            raise ValueError("audit events must be attributable to tenant+principal")


class AuditSink(Protocol):
    """Where audit events go. Must be append-only in production."""

    def emit(self, event: AuditEvent) -> None: ...

    def query(
        self, *, tenant_id: str, limit: int = 100
    ) -> Sequence[AuditEvent]: ...
