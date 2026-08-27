"""Governance plane tests.

The registry is a gate, so these tests assert that the gate actually closes,
and that the shipped governance data is loadable and internally consistent.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from inflexis.contracts.governance import (
    AISystemRecord,
    Applicability,
    ApprovalStatus,
    DeploymentStatus,
    RiskClass,
    TrainingRecord,
)
from inflexis.governance import AIRegistry, GovernanceError, load_matrix

REPO = Path(__file__).resolve().parents[2]


def _record(**overrides) -> AISystemRecord:
    base = dict(
        ai_system_id="assistant",
        tenant_id="acme-isd",
        name="Assistant",
        purpose="answer questions",
        use_case="policy_qa",
        owner="o",
        business_owner="b",
        technical_owner="t",
        risk_class=RiskClass.LIMITED,
        approval_status=ApprovalStatus.APPROVED,
        deployment_status=DeploymentStatus.PRODUCTION,
        next_review=date(2099, 1, 1),
    )
    base.update(overrides)
    return AISystemRecord(**base)


class TestRegistryIsAGate:
    def test_unregistered_system_cannot_serve(self):
        with pytest.raises(GovernanceError, match="not in the"):
            AIRegistry().assert_may_serve("acme-isd", "shadow-ai")

    def test_unapproved_system_cannot_serve(self):
        registry = AIRegistry([_record(approval_status=ApprovalStatus.UNDER_REVIEW)])
        with pytest.raises(GovernanceError, match="not approved"):
            registry.assert_may_serve("acme-isd", "assistant")

    def test_approved_pilot_system_may_serve(self):
        registry = AIRegistry([_record(deployment_status=DeploymentStatus.PILOT)])
        assert registry.assert_may_serve("acme-isd", "assistant").name == "Assistant"

    def test_registry_is_tenant_scoped(self):
        registry = AIRegistry([_record()])
        with pytest.raises(GovernanceError):
            registry.assert_may_serve("bravo-isd", "assistant")

    def test_prohibited_system_cannot_be_marked_deployed(self):
        with pytest.raises(ValueError, match="PROHIBITED"):
            _record(
                risk_class=RiskClass.PROHIBITED,
                deployment_status=DeploymentStatus.PRODUCTION,
            )

    def test_heightened_scrutiny_requires_documented_oversight(self):
        with pytest.raises(ValueError, match="human oversight"):
            _record(heightened_scrutiny=True, human_oversight="")


class TestReviewLifecycle:
    def test_approval_without_review_date_is_overdue(self):
        registry = AIRegistry([_record(next_review=None)])
        assert registry.overdue_reviews(), (
            "an approval with no review date must count as overdue"
        )

    def test_past_review_date_is_overdue(self):
        registry = AIRegistry([_record(next_review=date(2020, 1, 1))])
        assert len(registry.overdue_reviews(as_of=date(2026, 8, 26))) == 1

    def test_metrics_shape(self):
        registry = AIRegistry(
            [
                _record(),
                _record(
                    ai_system_id="draft-system",
                    approval_status=ApprovalStatus.DRAFT,
                    deployment_status=DeploymentStatus.NOT_DEPLOYED,
                ),
            ]
        )
        metrics = registry.metrics("acme-isd")
        assert metrics["total"] == 2
        assert metrics["approved"] == 1
        assert metrics["unapproved"] == 1


class TestTrainingRecords:
    def test_incomplete_training_is_not_current(self):
        record = TrainingRecord(
            tenant_id="acme-isd",
            employee_id="e1",
            role="teacher",
            training_id="AI-AWARE-101",
            assigned_date=date(2026, 1, 1),
        )
        assert not record.is_current(date(2026, 8, 26))

    def test_expired_training_is_not_current(self):
        record = TrainingRecord(
            tenant_id="acme-isd",
            employee_id="e1",
            role="teacher",
            training_id="AI-AWARE-101",
            assigned_date=date(2024, 1, 1),
            completed=True,
            completion_date=date(2024, 2, 1),
            expiration_date=date(2025, 2, 1),
        )
        assert not record.is_current(date(2026, 8, 26))
        assert record.is_current(date(2024, 6, 1))


class TestShippedGovernanceData:
    def test_texas_matrix_loads(self):
        matrix = load_matrix(REPO / "governance/texas/applicability-matrix.json")
        assert len(matrix) >= 8
        assert matrix.coverage()["implemented"] == len(matrix), (
            "every requirement row must name the control that implements it"
        )

    def test_no_row_claims_applicability_without_a_citation(self):
        matrix = load_matrix(REPO / "governance/texas/applicability-matrix.json")
        for row in matrix:
            assert row.citation_url.startswith("http"), row.requirement_id
            assert row.verification_status, row.requirement_id

    def test_unverified_rows_require_legal_review_or_are_not_asserted(self):
        """The core honesty property of the matrix.

        A row derived only from secondary sources must not assert that a
        requirement definitively applies to a district.
        """
        matrix = load_matrix(REPO / "governance/texas/applicability-matrix.json")
        for row in matrix:
            if row.verification_status == "secondary_source_only":
                assert row.district_applicability is not Applicability.APPLIES, (
                    f"{row.requirement_id} asserts APPLIES on secondary sources alone"
                )

    def test_ai_registry_fixture_matches_contract(self):
        payload = json.loads(
            (REPO / "governance/ai-registry/acme-isd-registry.json").read_text()
        )
        for system in payload["systems"]:
            RiskClass(system["risk_class"])
            ApprovalStatus(system["approval_status"])
            DeploymentStatus(system["deployment_status"])
            if system["risk_class"] == "prohibited":
                assert system["deployment_status"] == "not_deployed"
                assert system["approval_status"] == "rejected"

    def test_every_schema_is_valid_json_with_an_id(self):
        for path in sorted((REPO / "schemas").glob("*.json")):
            payload = json.loads(path.read_text())
            assert "$id" in payload, path.name
            assert "title" in payload, path.name
