"""Acme ISD -- the synthetic district.

Two tenants are defined. Acme ISD is the primary fixture; Bravo ISD exists so
that cross-tenant isolation is testable rather than assumed. Every document,
person, campus, and policy code below is invented.

The corpus is small but deliberately shaped to exercise the hard cases:

* a lexical-only match (``EIC(LOCAL)`` appears in exactly one document)
* a semantic-only match (phrasing that shares no tokens with the query)
* a superseded document alongside its replacement (freshness)
* two active versions at equal authority (conflict detection)
* an expired document (staleness)
* content in every trust domain a district would actually run
"""

from __future__ import annotations

from datetime import date

from ..contracts.classification import (
    AuthorityLevel,
    DataClassification,
    DocumentStatus,
    TrustDomain,
)
from ..contracts.document import (
    AccessControlList,
    Chunk,
    Document,
    Provenance,
    content_hash,
)
from ..contracts.identity import Permission, Principal, Role, Tenant
from ..retrieval.index import InMemoryIndex

ACME = Tenant(
    tenant_id="acme-isd",
    district_id="TX-ACME-001",
    display_name="Acme Independent School District",
    enabled_trust_domains=frozenset(
        {
            TrustDomain.PUBLIC.value,
            TrustDomain.DISTRICT_INTERNAL.value,
            TrustDomain.PERSONNEL.value,
            TrustDomain.STUDENT_CONFIDENTIAL.value,
        }
    ),
)

BRAVO = Tenant(
    tenant_id="bravo-isd",
    district_id="TX-BRAVO-002",
    display_name="Bravo Independent School District",
    enabled_trust_domains=frozenset(
        {TrustDomain.PUBLIC.value, TrustDomain.DISTRICT_INTERNAL.value}
    ),
)

CAMPUS_A = "CAMPUS-01-NORTH"
CAMPUS_B = "CAMPUS-02-SOUTH"

# Role bundles used when authoring ACLs. Authoring an ACL by listing every role
# by hand is how a role gets forgotten and a document silently becomes
# unreachable -- or worse, how a role gets added by accident.
ALL_STAFF = frozenset(
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
EVERYONE = ALL_STAFF | {Role.PUBLIC, Role.STUDENT}


def _doc(
    doc_id: str,
    title: str,
    doc_type: str,
    domain: TrustDomain,
    classification: DataClassification,
    authority: AuthorityLevel,
    acl: AccessControlList,
    text: str,
    *,
    tenant: Tenant = ACME,
    campus_id: str | None = None,
    department_id: str | None = None,
    status: DocumentStatus = DocumentStatus.ACTIVE,
    version: str = "1",
    effective_date: date | None = None,
    expiration_date: date | None = None,
    page_number: int | None = 1,
) -> tuple[Document, str]:
    document = Document(
        tenant_id=tenant.tenant_id,
        district_id=tenant.district_id,
        document_id=doc_id,
        title=title,
        document_type=doc_type,
        trust_domain=domain,
        data_classification=classification,
        authority_level=authority,
        acl=acl,
        provenance=Provenance(
            source_system="synthetic",
            source_uri=f"synthetic://{tenant.tenant_id}/{doc_id}",
            content_hash=content_hash(text),
            page_number=page_number,
        ),
        status=status,
        version=version,
        campus_id=campus_id,
        department_id=department_id,
        effective_date=effective_date,
        expiration_date=expiration_date,
    )
    return document, text


def acme_documents() -> list[tuple[Document, str]]:
    """The synthetic Acme ISD corpus."""
    public_acl = AccessControlList(allowed_roles=EVERYONE)
    staff_acl = AccessControlList(allowed_roles=ALL_STAFF)
    hr_acl = AccessControlList(
        allowed_roles=frozenset({Role.HR, Role.SUPERINTENDENT}),
        required_permissions=frozenset({Permission.RETRIEVE_PERSONNEL}),
    )
    student_acl = AccessControlList(
        allowed_roles=frozenset(
            {Role.COUNSELOR, Role.PRINCIPAL, Role.SUPERINTENDENT}
        ),
        required_permissions=frozenset({Permission.RETRIEVE_STUDENT}),
    )
    campus_a_acl = AccessControlList(
        allowed_roles=ALL_STAFF, attribute_match=(("campus_id", CAMPUS_A),)
    )
    campus_b_acl = AccessControlList(
        allowed_roles=ALL_STAFF, attribute_match=(("campus_id", CAMPUS_B),)
    )

    return [
        # --- Public / board policy -------------------------------------
        _doc(
            "BP-EIC-LOCAL",
            "Board Policy EIC(LOCAL) - Academic Achievement: Class Ranking",
            "board_policy",
            TrustDomain.PUBLIC,
            DataClassification.PUBLIC,
            AuthorityLevel.BOARD_POLICY,
            public_acl,
            "Board Policy EIC(LOCAL) governs class ranking and grade point "
            "average calculation for Acme ISD. Class rank shall be computed at "
            "the end of the eleventh grade and again after the third six weeks "
            "of the twelfth grade. Only courses designated as ranked courses in "
            "the district course catalog are included in the class rank "
            "calculation. Questions about EIC(LOCAL) are directed to the "
            "campus counseling office.",
            effective_date=date(2025, 8, 1),
        ),
        _doc(
            "BP-FNG-LOCAL",
            "Board Policy FNG(LOCAL) - Student Complaints and Grievances",
            "board_policy",
            TrustDomain.PUBLIC,
            DataClassification.PUBLIC,
            AuthorityLevel.BOARD_POLICY,
            public_acl,
            "Board Policy FNG(LOCAL) establishes the three level complaint "
            "process for students and parents. A Level One complaint is filed "
            "with the campus principal within fifteen district business days. "
            "A Level Two appeal is filed with the superintendent or designee. "
            "A Level Three appeal is presented to the board of trustees.",
            effective_date=date(2025, 8, 1),
        ),
        _doc(
            "TEC-25085-SUMMARY",
            "Compulsory Attendance Summary - Texas Education Code 25.085",
            "state_law_summary",
            TrustDomain.PUBLIC,
            DataClassification.PUBLIC,
            AuthorityLevel.STATE_LAW,
            public_acl,
            "Texas Education Code 25.085 requires a child who is at least six "
            "years of age, or who is younger than six and has previously been "
            "enrolled in first grade, and who has not yet reached the child's "
            "nineteenth birthday, to attend school. Compulsory attendance also "
            "applies to students enrolled in prekindergarten or kindergarten.",
            effective_date=date(2025, 9, 1),
        ),
        # --- Semantic-only match: no shared tokens with the natural query --
        _doc(
            "HB-TARDY-GUIDE",
            "Campus Punctuality Expectations",
            "handbook",
            TrustDomain.PUBLIC,
            DataClassification.PUBLIC,
            AuthorityLevel.DISTRICT_HANDBOOK,
            public_acl,
            "Students arriving after the first bell are marked late by the "
            "attendance clerk. Repeated lateness results in a conference with "
            "an assistant principal and may lead to after school detention.",
            effective_date=date(2025, 8, 1),
        ),
        # --- District internal -----------------------------------------
        _doc(
            "SOP-IT-PASSWORD",
            "IT Standard Operating Procedure - Account Lockout and Reset",
            "sop",
            TrustDomain.DISTRICT_INTERNAL,
            DataClassification.INTERNAL,
            AuthorityLevel.DISTRICT_PROCEDURE,
            staff_acl,
            "Staff account lockouts are released by the service desk after "
            "identity verification. A staff member must present a district "
            "badge or complete a callback to the number on file. Password "
            "resets for student accounts are performed by campus technology "
            "staff. Service desk technicians never reset an administrator "
            "account without a second approver.",
            department_id="DEPT-IT",
            effective_date=date(2026, 1, 15),
        ),
        _doc(
            "SOP-PURCHASING",
            "Purchasing Procedure - Requisition Approval Thresholds",
            "sop",
            TrustDomain.DISTRICT_INTERNAL,
            DataClassification.INTERNAL,
            AuthorityLevel.DISTRICT_PROCEDURE,
            staff_acl,
            "Requisitions under two thousand five hundred dollars are approved "
            "by the campus principal. Requisitions between two thousand five "
            "hundred and fifty thousand dollars require business office review. "
            "Purchases above fifty thousand dollars require board approval "
            "under the district purchasing policy.",
            department_id="DEPT-BUSINESS",
            effective_date=date(2025, 9, 1),
        ),
        # --- Superseded / replacement pair (freshness) ------------------
        _doc(
            "AR-GRADING-2019",
            "Administrative Regulation - Grading and Reporting (2019)",
            "administrative_regulation",
            TrustDomain.DISTRICT_INTERNAL,
            DataClassification.INTERNAL,
            AuthorityLevel.ADMINISTRATIVE_REGULATION,
            staff_acl,
            "Teachers record a minimum of nine grades per nine week grading "
            "period. Late work is accepted for a maximum of seventy percent "
            "credit within five school days.",
            status=DocumentStatus.SUPERSEDED,
            version="2019.1",
            effective_date=date(2019, 8, 1),
            expiration_date=date(2025, 7, 31),
        ),
        _doc(
            "AR-GRADING-2025",
            "Administrative Regulation - Grading and Reporting (2025)",
            "administrative_regulation",
            TrustDomain.DISTRICT_INTERNAL,
            DataClassification.INTERNAL,
            AuthorityLevel.ADMINISTRATIVE_REGULATION,
            staff_acl,
            "Teachers record a minimum of twelve grades per nine week grading "
            "period. Late work is accepted for a maximum of eighty percent "
            "credit within five school days. Reteach and retest opportunities "
            "are offered for any major assessment below seventy percent.",
            version="2025.1",
            effective_date=date(2025, 8, 1),
        ),
        # --- Expired document (staleness) -------------------------------
        _doc(
            "MEMO-COVID-PROTOCOL",
            "Temporary Health Screening Memo",
            "memo",
            TrustDomain.DISTRICT_INTERNAL,
            DataClassification.INTERNAL,
            AuthorityLevel.DEPARTMENT_DOC,
            staff_acl,
            "Campus health screening stations operate at each entrance during "
            "the temporary screening period described in this memo.",
            effective_date=date(2021, 1, 4),
            expiration_date=date(2022, 6, 30),
        ),
        # --- Campus-scoped pair (ABAC) ----------------------------------
        _doc(
            "CAMPUS-A-BELL",
            "North Campus Bell Schedule and Duty Roster",
            "campus_doc",
            TrustDomain.DISTRICT_INTERNAL,
            DataClassification.INTERNAL,
            AuthorityLevel.CAMPUS_DOC,
            campus_a_acl,
            "North Campus first period begins at eight fifteen. Morning duty "
            "posts are assigned in the north hallway and the bus loop.",
            campus_id=CAMPUS_A,
            effective_date=date(2025, 8, 1),
        ),
        _doc(
            "CAMPUS-B-BELL",
            "South Campus Bell Schedule and Restricted Incident Notes",
            "campus_doc",
            TrustDomain.DISTRICT_INTERNAL,
            DataClassification.CONFIDENTIAL,
            AuthorityLevel.CAMPUS_DOC,
            campus_b_acl,
            "South Campus first period begins at eight forty. Restricted "
            "incident follow up notes for the south campus are maintained by "
            "the campus administration team.",
            campus_id=CAMPUS_B,
            effective_date=date(2025, 8, 1),
        ),
        # --- Personnel / HR ---------------------------------------------
        _doc(
            "HR-SALARY-SCHEDULE",
            "Personnel Compensation Schedule and Individual Placement Notes",
            "hr_record",
            TrustDomain.PERSONNEL,
            DataClassification.CONFIDENTIAL,
            AuthorityLevel.DEPARTMENT_DOC,
            hr_acl,
            "The teacher compensation schedule places each employee by years "
            "of creditable service. Individual placement exceptions, salary "
            "negotiations, and performance improvement plans for named "
            "employees are recorded in this personnel file.",
            department_id="DEPT-HR",
            effective_date=date(2025, 8, 1),
        ),
        _doc(
            "HR-GRIEVANCE-FILE",
            "Employee Grievance Case Notes",
            "hr_record",
            TrustDomain.PERSONNEL,
            DataClassification.RESTRICTED,
            AuthorityLevel.DEPARTMENT_DOC,
            hr_acl,
            "Case notes for employee grievance matters, including investigator "
            "findings and recommended disciplinary outcomes for named staff.",
            department_id="DEPT-HR",
            effective_date=date(2025, 8, 1),
        ),
        # --- Student confidential ---------------------------------------
        _doc(
            "SPED-504-CASE",
            "Section 504 Accommodation Case File",
            "student_record",
            TrustDomain.STUDENT_CONFIDENTIAL,
            DataClassification.RESTRICTED,
            AuthorityLevel.DEPARTMENT_DOC,
            student_acl,
            "Section 504 accommodation plans and individual student "
            "accommodation case notes, including evaluation results and "
            "parental consent records for named students.",
            department_id="DEPT-SPED",
            effective_date=date(2025, 8, 1),
        ),
        _doc(
            "DISCIPLINE-DAEP-CASE",
            "DAEP Placement Case Notes",
            "student_record",
            TrustDomain.STUDENT_CONFIDENTIAL,
            DataClassification.RESTRICTED,
            AuthorityLevel.DEPARTMENT_DOC,
            student_acl,
            "Disciplinary alternative education program placement records, "
            "including hearing outcomes and placement duration for named "
            "students referred under the student code of conduct.",
            department_id="DEPT-STUDENT-SERVICES",
            effective_date=date(2025, 8, 1),
        ),
    ]


def bravo_documents() -> list[tuple[Document, str]]:
    """A minimal second-tenant corpus, used only for isolation testing."""
    public_acl = AccessControlList(allowed_roles=EVERYONE)
    staff_acl = AccessControlList(allowed_roles=ALL_STAFF)
    return [
        _doc(
            "BRAVO-BP-EIC-LOCAL",
            "Bravo ISD Board Policy EIC(LOCAL) - Class Ranking",
            "board_policy",
            TrustDomain.PUBLIC,
            DataClassification.PUBLIC,
            AuthorityLevel.BOARD_POLICY,
            public_acl,
            "Bravo ISD Board Policy EIC(LOCAL) governs class ranking. Bravo "
            "ISD computes class rank once at the end of the twelfth grade.",
            tenant=BRAVO,
            effective_date=date(2025, 8, 1),
        ),
        _doc(
            "BRAVO-SOP-IT",
            "Bravo ISD IT Procedure - Account Lockout",
            "sop",
            TrustDomain.DISTRICT_INTERNAL,
            DataClassification.INTERNAL,
            AuthorityLevel.DISTRICT_PROCEDURE,
            staff_acl,
            "Bravo ISD service desk releases account lockouts after identity "
            "verification using the Bravo ISD badge system.",
            tenant=BRAVO,
            effective_date=date(2025, 8, 1),
        ),
    ]


def _to_chunks(pairs: list[tuple[Document, str]]) -> list[Chunk]:
    return [
        Chunk.from_document(doc, chunk_id=f"{doc.document_id}#0", text=text)
        for doc, text in pairs
    ]


def build_acme_index() -> InMemoryIndex:
    index = InMemoryIndex()
    index.add_all(_to_chunks(acme_documents()))
    return index


def build_two_tenant_index() -> InMemoryIndex:
    """Both districts in one index -- the shape that makes leakage possible.

    Co-locating tenants is the realistic deployment (one search service, many
    districts) and therefore the configuration the isolation tests must run
    against. Testing isolation with one tenant per index proves nothing.
    """
    index = InMemoryIndex()
    index.add_all(_to_chunks(acme_documents()))
    index.add_all(_to_chunks(bravo_documents()))
    return index


def principals() -> dict[str, Principal]:
    """Synthetic people. Names are fabricated."""
    base = {Permission.RETRIEVE}
    return {
        "public": Principal(
            subject_id="anon-visitor",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.PUBLIC}),
            permissions=frozenset(base),
        ),
        "student": Principal(
            subject_id="student-1001",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.STUDENT}),
            permissions=frozenset(base),
            attributes={"campus_id": CAMPUS_A},
        ),
        "teacher": Principal(
            subject_id="staff-teacher-2001",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.TEACHER}),
            permissions=frozenset(base | {Permission.TOOL_INVOKE_READ}),
            attributes={"campus_id": CAMPUS_A, "department_id": "DEPT-ELA"},
        ),
        "teacher_campus_b": Principal(
            subject_id="staff-teacher-2002",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.TEACHER}),
            permissions=frozenset(base),
            attributes={"campus_id": CAMPUS_B},
        ),
        "counselor": Principal(
            subject_id="staff-counselor-3001",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.COUNSELOR}),
            permissions=frozenset(base | {Permission.RETRIEVE_STUDENT}),
            attributes={"campus_id": CAMPUS_A},
        ),
        "principal": Principal(
            subject_id="staff-principal-4001",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.PRINCIPAL}),
            permissions=frozenset(base | {Permission.RETRIEVE_STUDENT}),
            attributes={"campus_id": CAMPUS_A},
        ),
        "hr": Principal(
            subject_id="staff-hr-5001",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.HR}),
            permissions=frozenset(base | {Permission.RETRIEVE_PERSONNEL}),
            attributes={"department_id": "DEPT-HR"},
        ),
        "it_admin": Principal(
            subject_id="staff-it-6001",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.IT_ADMIN}),
            permissions=frozenset(
                base | {Permission.TOOL_INVOKE_READ, Permission.AUDIT_READ}
            ),
            attributes={"department_id": "DEPT-IT"},
        ),
        "superintendent": Principal(
            subject_id="staff-supt-7001",
            tenant_id=ACME.tenant_id,
            roles=frozenset({Role.SUPERINTENDENT}),
            permissions=frozenset(
                base
                | {Permission.RETRIEVE_PERSONNEL, Permission.RETRIEVE_STUDENT}
            ),
        ),
        # A teacher at the *other* district, for cross-tenant testing.
        "bravo_teacher": Principal(
            subject_id="bravo-teacher-9001",
            tenant_id=BRAVO.tenant_id,
            roles=frozenset({Role.TEACHER}),
            permissions=frozenset(base),
        ),
    }
