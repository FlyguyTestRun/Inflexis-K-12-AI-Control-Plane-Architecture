"""Trust domains, data classification, and authority ranking.

These three axes are deliberately separate:

* :class:`TrustDomain`   -- *where the content lives* (index partitioning)
* :class:`DataClassification` -- *how sensitive the content is* (handling rules)
* :class:`AuthorityLevel`     -- *how much the content should be believed*

Conflating them is a common design error. A public web page and a board policy
may both be non-sensitive, but they carry wildly different authority. A campus
handbook and a legal memo may both be authoritative, but carry wildly different
handling requirements.
"""

from __future__ import annotations

from enum import Enum, StrEnum


class TrustDomain(StrEnum):
    """Index partitions. Content never crosses a partition implicitly.

    The letters match the taxonomy in ``docs/security/trust-boundaries.md``.
    A district may map its own labels onto these domains via tenant config,
    but the number and ordering of domains is a platform invariant.
    """

    PUBLIC = "A_public"
    DISTRICT_INTERNAL = "B_district_internal"
    PERSONNEL = "C_personnel_hr"
    STUDENT_CONFIDENTIAL = "D_student_confidential"
    HIGHLY_SENSITIVE = "E_highly_sensitive_sped"
    LEGAL_PRIVILEGED = "F_legal_privileged"
    SECURITY_CREDENTIALS = "G_security_credentials"


#: Trust domains that must never be retrievable by a general-purpose assistant,
#: regardless of the caller's roles. Access requires a dedicated, separately
#: approved AI use case with its own risk assessment (see ADR-003).
RESTRICTED_BY_DEFAULT: frozenset[TrustDomain] = frozenset(
    {
        TrustDomain.LEGAL_PRIVILEGED,
        TrustDomain.SECURITY_CREDENTIALS,
    }
)


class DataClassification(StrEnum):
    """Handling sensitivity, independent of storage location."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AuthorityLevel(int, Enum):
    """Source authority ranking. Lower ordinal == higher authority.

    Used by the corrective-RAG authority check to decide whether retrieved
    evidence is good enough to answer with, and to detect the case where a
    low-authority source contradicts a high-authority one.

    The default ordering encodes the hierarchy in ``docs/architecture.md`` s15.
    Districts may override the ranking of levels 4-10 through tenant config;
    levels 1-3 are not district-configurable because state law and
    board-approved policy outrank local documentation by definition.
    """

    STATE_LAW = 1
    BOARD_POLICY = 2
    ADMINISTRATIVE_REGULATION = 3
    DISTRICT_PROCEDURE = 4
    DISTRICT_HANDBOOK = 5
    DEPARTMENT_DOC = 6
    CAMPUS_DOC = 7
    APPROVED_INTERNAL = 8
    APPROVED_EXTERNAL = 9
    PUBLIC_WEB = 10

    @property
    def is_district_configurable(self) -> bool:
        return self.value >= 4


#: Authority at or above which a source may be cited as definitive for a
#: policy/compliance question without an accompanying "verify with staff"
#: caveat. Configurable per use case; this is the platform default.
DEFAULT_AUTHORITATIVE_THRESHOLD = AuthorityLevel.DISTRICT_HANDBOOK


class DocumentStatus(StrEnum):
    """Lifecycle state. Only ACTIVE content is retrievable by default."""

    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    ARCHIVED = "archived"
    REVOKED = "revoked"


#: Statuses eligible for retrieval unless a use case explicitly opts in to more
#: (for example, a records-research use case that needs superseded policy).
RETRIEVABLE_STATUSES: frozenset[DocumentStatus] = frozenset({DocumentStatus.ACTIVE})
