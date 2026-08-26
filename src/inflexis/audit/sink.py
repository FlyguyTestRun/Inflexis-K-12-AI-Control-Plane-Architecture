"""Reference audit sink.

Production deployments write to an append-only store (Azure Monitor / a
write-once table). This in-memory implementation exists for tests and local
development and enforces the same append-only property so that test code cannot
develop habits the production sink will not tolerate.
"""

from __future__ import annotations

from typing import Sequence

from ..contracts.audit import AuditEvent, AuditEventType, Severity


class InMemoryAuditSink:
    """Append-only, tenant-partitioned audit log."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def emit(self, event: AuditEvent) -> None:
        self._events.append(event)

    def query(
        self, *, tenant_id: str, limit: int = 100
    ) -> Sequence[AuditEvent]:
        return [e for e in self._events if e.tenant_id == tenant_id][:limit]

    # -- test/ops helpers ---------------------------------------------------

    @property
    def events(self) -> Sequence[AuditEvent]:
        return tuple(self._events)

    def of_type(self, event_type: AuditEventType) -> list[AuditEvent]:
        return [e for e in self._events if e.event_type is event_type]

    def security_events(self) -> list[AuditEvent]:
        return [
            e
            for e in self._events
            if e.severity in (Severity.SECURITY, Severity.CRITICAL)
        ]
