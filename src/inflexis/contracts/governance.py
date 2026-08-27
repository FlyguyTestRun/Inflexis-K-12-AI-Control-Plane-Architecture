"""Governance contracts (Plane 1).

The AI inventory, use-case registry, risk classification, and the applicability
model that keeps legal requirements *configurable and reviewable* rather than
hard-coded as legal conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class RiskClass(StrEnum):
    MINIMAL = "minimal"
    LIMITED = "limited"
    ELEVATED = "elevated"
    HEIGHTENED_SCRUTINY = "heightened_scrutiny"
    PROHIBITED = "prohibited"


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class DeploymentStatus(StrEnum):
    NOT_DEPLOYED = "not_deployed"
    SANDBOX = "sandbox"
    PILOT = "pilot"
    PRODUCTION = "production"
    DECOMMISSIONED = "decommissioned"


class Applicability(StrEnum):
    """Whether a requirement applies -- never asserted, always reviewed.

    The platform ships defaults and citations. A district's counsel sets the
    final value. ``REQUIRES_LEGAL_REVIEW`` is the honest default for anything
    the platform cannot determine from the statute text alone.
    """

    APPLIES = "applies"
    DOES_NOT_APPLY = "does_not_apply"
    CONDITIONAL = "conditional"
    REQUIRES_LEGAL_REVIEW = "requires_legal_review"
    RECOMMENDED_PRACTICE = "recommended_practice"


@dataclass(frozen=True, slots=True)
class AISystemRecord:
    """One entry in the district AI inventory.

    An AI system that is not in this registry must not be reachable in
    production; the gateway rejects traffic carrying an unknown
    ``ai_system_id``.
    """

    ai_system_id: str
    tenant_id: str
    name: str
    purpose: str
    use_case: str
    owner: str
    business_owner: str
    technical_owner: str
    risk_class: RiskClass
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    deployment_status: DeploymentStatus = DeploymentStatus.NOT_DEPLOYED
    affected_users: tuple[str, ...] = ()
    affected_population: str = ""
    data_categories: frozenset[str] = field(default_factory=frozenset)
    models: tuple[str, ...] = ()
    vendors: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    heightened_scrutiny: bool = False
    human_oversight: str = ""
    evaluation_status: str = "not_started"
    policy_version: str = ""
    last_reviewed: date | None = None
    next_review: date | None = None

    def __post_init__(self) -> None:
        if self.risk_class is RiskClass.PROHIBITED and self.deployment_status in (
            DeploymentStatus.PILOT,
            DeploymentStatus.PRODUCTION,
        ):
            raise ValueError(
                f"AI system {self.ai_system_id!r} is classified PROHIBITED but "
                f"marked {self.deployment_status.value}"
            )
        if self.heightened_scrutiny and not self.human_oversight:
            raise ValueError(
                f"AI system {self.ai_system_id!r} is heightened-scrutiny and must "
                "document a human oversight mechanism"
            )

    @property
    def may_serve_production(self) -> bool:
        return (
            self.approval_status is ApprovalStatus.APPROVED
            and self.deployment_status
            in (DeploymentStatus.PILOT, DeploymentStatus.PRODUCTION)
            and self.risk_class is not RiskClass.PROHIBITED
        )


@dataclass(frozen=True, slots=True)
class RequirementMapping:
    """One row of a governance applicability matrix.

    Deliberately carries ``citation`` and ``legal_review_required`` so that the
    repository never states a legal conclusion in its own voice.
    """

    requirement_id: str
    source: str
    statute_or_rule: str
    citation_url: str
    actor: str
    summary: str
    district_applicability: Applicability
    use_case_applicability: str
    required_control: str
    implemented_by: str
    evidence: str
    legal_review_required: bool = True
    verification_status: str = "unverified"
    notes: str = ""


@dataclass(frozen=True, slots=True)
class TrainingRecord:
    """AI awareness / cybersecurity training evidence (HB 3512 pattern)."""

    tenant_id: str
    employee_id: str
    role: str
    training_id: str
    assigned_date: date
    completed: bool = False
    completion_date: date | None = None
    certification_id: str = ""
    expiration_date: date | None = None
    evidence_uri: str = ""

    def is_current(self, as_of: date) -> bool:
        if not self.completed or self.completion_date is None:
            return False
        if self.expiration_date and as_of > self.expiration_date:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ModernizationMeasurement:
    """Before/after measurement for an AI-assisted process (HB 2818 theme).

    Note: HB 2818 creates an AI division within DIR for state legacy-system
    modernization. It is not, on its face, a measurement mandate imposed on
    school districts. This record exists because districts need to demonstrate
    value -- see ``docs/governance/texas-applicability.md`` for the distinction.
    """

    tenant_id: str
    project_id: str
    legacy_process: str
    baseline_minutes: float
    baseline_cost_usd: float
    baseline_headcount: float
    ai_assisted_minutes: float
    ai_assisted_cost_usd: float
    ai_assisted_headcount: float
    quality_change: str = ""
    outcome: str = ""
    measurement_method: str = ""

    @property
    def minutes_saved(self) -> float:
        return self.baseline_minutes - self.ai_assisted_minutes

    @property
    def roi(self) -> float | None:
        """Return on investment, or None when the baseline cost is zero."""
        if self.baseline_cost_usd == 0:
            return None
        return (
            self.baseline_cost_usd - self.ai_assisted_cost_usd
        ) / self.baseline_cost_usd
