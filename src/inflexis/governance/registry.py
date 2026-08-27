"""The AI inventory and use-case registry.

The registry answers the question a district will be asked first in any audit:
*what AI is running here, who owns it, what data does it touch, and who
approved it?*

Making the registry a gate rather than a spreadsheet is the whole point. A
spreadsheet drifts; a gate cannot.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import date

from ..contracts.governance import (
    AISystemRecord,
    ApprovalStatus,
    DeploymentStatus,
    RiskClass,
)


class GovernanceError(RuntimeError):
    """Raised when an ungoverned or unapproved AI system attempts to serve."""


class AIRegistry:
    """Tenant-scoped AI system inventory."""

    def __init__(self, records: Iterable[AISystemRecord] = ()) -> None:
        self._records: dict[tuple[str, str], AISystemRecord] = {}
        for record in records:
            self.register(record)

    def register(self, record: AISystemRecord) -> None:
        self._records[(record.tenant_id, record.ai_system_id)] = record

    def get(self, tenant_id: str, ai_system_id: str) -> AISystemRecord | None:
        return self._records.get((tenant_id, ai_system_id))

    def __iter__(self) -> Iterator[AISystemRecord]:
        return iter(self._records.values())

    def for_tenant(self, tenant_id: str) -> list[AISystemRecord]:
        return [r for r in self._records.values() if r.tenant_id == tenant_id]

    def assert_may_serve(self, tenant_id: str, ai_system_id: str) -> AISystemRecord:
        """Gate called by the AI gateway before any request is processed."""
        record = self.get(tenant_id, ai_system_id)
        if record is None:
            raise GovernanceError(
                f"AI system {ai_system_id!r} is not in the {tenant_id!r} inventory; "
                "unregistered AI systems cannot serve traffic"
            )
        if record.risk_class is RiskClass.PROHIBITED:
            raise GovernanceError(
                f"AI system {ai_system_id!r} is classified PROHIBITED"
            )
        if record.approval_status is not ApprovalStatus.APPROVED:
            raise GovernanceError(
                f"AI system {ai_system_id!r} is {record.approval_status.value}, "
                "not approved"
            )
        if record.deployment_status not in (
            DeploymentStatus.PILOT,
            DeploymentStatus.PRODUCTION,
        ):
            raise GovernanceError(
                f"AI system {ai_system_id!r} is {record.deployment_status.value}"
            )
        return record

    # -- review lifecycle ---------------------------------------------------

    def overdue_reviews(self, as_of: date | None = None) -> list[AISystemRecord]:
        """Systems past their review date.

        An approval with no review date is treated as overdue rather than
        permanent. "Approved once in 2026" is not a governance posture.
        """
        as_of = as_of or date.today()
        overdue = []
        for record in self._records.values():
            if record.approval_status is not ApprovalStatus.APPROVED:
                continue
            if record.next_review is None or record.next_review < as_of:
                overdue.append(record)
        return overdue

    def heightened_scrutiny_systems(self) -> list[AISystemRecord]:
        return [
            r
            for r in self._records.values()
            if r.heightened_scrutiny or r.risk_class is RiskClass.HEIGHTENED_SCRUTINY
        ]

    def metrics(self, tenant_id: str) -> dict[str, int]:
        """The governance metrics from docs/evaluation/evaluation-framework.md."""
        records = self.for_tenant(tenant_id)
        return {
            "total": len(records),
            "approved": sum(
                1 for r in records if r.approval_status is ApprovalStatus.APPROVED
            ),
            "unapproved": sum(
                1 for r in records if r.approval_status is not ApprovalStatus.APPROVED
            ),
            "in_production": sum(
                1
                for r in records
                if r.deployment_status is DeploymentStatus.PRODUCTION
            ),
            "heightened_scrutiny": sum(1 for r in records if r.heightened_scrutiny),
            "overdue_review": sum(
                1 for r in self.overdue_reviews() if r.tenant_id == tenant_id
            ),
        }
