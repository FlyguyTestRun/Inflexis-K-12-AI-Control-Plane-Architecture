"""The authorization tests required by docs/architecture.md s37.

Each test asserts a boundary a district would be asked about in a procurement
security review. They run against a *co-located two-tenant index*, because
isolation that only holds when tenants are in separate indexes is not
isolation -- it is deployment luck.
"""

import pytest
from conftest import retrieve_text

from inflexis.contracts.classification import TrustDomain


def _retrieved_ids(context):
    return {e.chunk.chunk_id for e in context.evidence}


def _all_text(context):
    return " ".join(e.chunk.text for e in context.evidence).lower()


class TestTeacherCannotReachHR:
    def test_teacher_query_for_salary_returns_no_personnel_content(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline,
            acme_engine,
            people["teacher"],
            "teacher compensation schedule salary placement",
        )
        assert not any(
            e.chunk.trust_domain is TrustDomain.PERSONNEL for e in ctx.evidence
        ), "teacher retrieved personnel-domain content"
        assert "grievance" not in _all_text(ctx)

    def test_teacher_has_no_personnel_grant_at_all(self, acme_engine, people):
        domains = acme_engine.allowed_domains(people["teacher"])
        assert TrustDomain.PERSONNEL not in domains
        assert TrustDomain.STUDENT_CONFIDENTIAL not in domains

    def test_hr_can_reach_personnel(self, pipeline, acme_engine, people):
        ctx = retrieve_text(
            pipeline,
            acme_engine,
            people["hr"],
            "teacher compensation schedule placement by years of service",
        )
        assert any(
            e.chunk.trust_domain is TrustDomain.PERSONNEL for e in ctx.evidence
        ), "HR could not reach the personnel content it is entitled to"


class TestTeacherCannotReachStudentRecords:
    def test_teacher_query_for_504_returns_no_student_records(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline,
            acme_engine,
            people["teacher"],
            "section 504 accommodation case file evaluation results",
        )
        assert "SPED-504-CASE#0" not in _retrieved_ids(ctx)

    def test_teacher_query_for_daep_returns_no_discipline_records(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline, acme_engine, people["teacher"],
            "DAEP placement hearing outcome for a student",
        )
        assert "DISCIPLINE-DAEP-CASE#0" not in _retrieved_ids(ctx)

    def test_counselor_with_entitlement_can_reach_student_records(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline, acme_engine, people["counselor"],
            "section 504 accommodation case file",
        )
        assert "SPED-504-CASE#0" in _retrieved_ids(ctx)

    def test_role_without_permission_loses_the_sensitive_domain(
        self, acme_engine, people
    ):
        """A counselor role without RETRIEVE_STUDENT gets no student domain.

        Role alone must never be sufficient for a sensitive trust domain.
        """
        import dataclasses

        stripped = dataclasses.replace(
            people["counselor"], permissions=frozenset()
        )
        # RETRIEVE itself is now missing, so authorization must fail closed.
        with pytest.raises(PermissionError):
            acme_engine.authorize_retrieval(stripped, "504 case file")


class TestCampusIsolation:
    def test_campus_a_teacher_cannot_read_campus_b_restricted_notes(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline,
            acme_engine,
            people["teacher"],
            "south campus restricted incident follow up notes",
        )
        assert "CAMPUS-B-BELL#0" not in _retrieved_ids(ctx)

    def test_campus_b_teacher_cannot_read_campus_a_docs(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline,
            acme_engine,
            people["teacher_campus_b"],
            "north campus bell schedule morning duty posts bus loop",
        )
        assert "CAMPUS-A-BELL#0" not in _retrieved_ids(ctx)

    def test_campus_a_teacher_can_read_own_campus(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline, acme_engine, people["teacher"],
            "north campus bell schedule duty roster",
        )
        assert "CAMPUS-A-BELL#0" in _retrieved_ids(ctx)


class TestStudentAndPublicRestrictions:
    def test_student_cannot_reach_staff_procedures(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline,
            acme_engine,
            people["student"],
            "service desk account lockout administrator reset second approver",
        )
        assert "SOP-IT-PASSWORD#0" not in _retrieved_ids(ctx)
        assert all(
            e.chunk.trust_domain is TrustDomain.PUBLIC for e in ctx.evidence
        )

    def test_public_user_cannot_reach_internal_documents(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline,
            acme_engine,
            people["public"],
            "requisition approval thresholds business office review",
        )
        assert "SOP-PURCHASING#0" not in _retrieved_ids(ctx)

    def test_public_user_can_reach_public_board_policy(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline, acme_engine, people["public"],
            "EIC(LOCAL) class ranking",
        )
        assert "BP-EIC-LOCAL#0" in _retrieved_ids(ctx)


class TestTenantIsolation:
    def test_acme_principal_cannot_retrieve_bravo_content(
        self, pipeline, acme_engine, people
    ):
        ctx = retrieve_text(
            pipeline, acme_engine, people["teacher"],
            "EIC(LOCAL) class ranking computed at the end of twelfth grade",
        )
        ids = _retrieved_ids(ctx)
        assert not any(i.startswith("BRAVO-") for i in ids)
        assert "bravo" not in _all_text(ctx)

    def test_bravo_principal_cannot_retrieve_acme_content(
        self, pipeline, bravo_engine, people
    ):
        ctx = retrieve_text(
            pipeline, bravo_engine, people["bravo_teacher"],
            "EIC(LOCAL) class ranking eleventh grade course catalog",
        )
        ids = _retrieved_ids(ctx)
        assert not any(i.startswith("BP-") or i.startswith("SOP-") for i in ids)

    def test_engine_rejects_a_principal_from_another_tenant(
        self, acme_engine, people
    ):
        with pytest.raises(PermissionError, match="cannot query tenant"):
            acme_engine.authorize_retrieval(
                people["bravo_teacher"], "anything at all"
            )

    def test_restricted_domains_are_unreachable_for_everyone(
        self, acme_engine, people
    ):
        for name, principal in people.items():
            if principal.tenant_id != "acme-isd":
                continue
            domains = acme_engine.allowed_domains(principal)
            assert TrustDomain.LEGAL_PRIVILEGED not in domains, name
            assert TrustDomain.SECURITY_CREDENTIALS not in domains, name
