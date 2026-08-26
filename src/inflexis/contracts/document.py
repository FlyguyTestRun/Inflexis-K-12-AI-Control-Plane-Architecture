"""Document, chunk, ACL, and provenance contracts.

Every retrievable unit in the platform carries enough metadata to answer four
questions *before* it reaches a model:

1. Whose is it?        -- tenant_id / district_id / campus_id / department_id
2. Who may see it?     -- trust_domain / acl / required_permissions
3. Should it be believed? -- authority_level / status / effective dates
4. Where did it come from? -- provenance (source_uri, page, content_hash)

A chunk that cannot answer all four is not retrievable. This is enforced in
:meth:`Chunk.validate`, not left to ingestion discipline.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Sequence

from .classification import (
    AuthorityLevel,
    DataClassification,
    DocumentStatus,
    TrustDomain,
)
from .identity import Permission, Principal, Role


@dataclass(frozen=True, slots=True)
class AccessControlList:
    """Per-document access control.

    Empty ``allowed_roles`` means "no role grants access" -- deliberately
    fail-closed. A document intended to be broadly readable must say so
    explicitly. This is the opposite of the usual default and it is the
    correct default for student and personnel data.
    """

    allowed_roles: frozenset[Role] = field(default_factory=frozenset)
    required_permissions: frozenset[Permission] = field(default_factory=frozenset)
    #: Explicit subject allow-list, used for narrowly shared documents.
    allowed_subjects: frozenset[str] = field(default_factory=frozenset)
    #: ABAC predicates that must match the principal's attributes exactly.
    #: e.g. {"campus_id": "CAMPUS-01"} restricts to one campus.
    attribute_match: tuple[tuple[str, str], ...] = ()

    def permits(self, principal: Principal) -> bool:
        """Fail-closed access check for a single principal."""
        if principal.subject_id in self.allowed_subjects:
            role_ok = True
        else:
            role_ok = bool(self.allowed_roles & principal.roles)
        if not role_ok:
            return False
        if not self.required_permissions <= principal.permissions:
            return False
        for key, expected in self.attribute_match:
            if principal.attributes.get(key) != expected:
                return False
        return True


@dataclass(frozen=True, slots=True)
class Provenance:
    """Where a piece of evidence came from, precisely enough to cite it."""

    source_system: str
    source_uri: str
    content_hash: str
    page_number: int | None = None
    section: str | None = None
    table_id: str | None = None
    image_id: str | None = None
    #: Set for content produced by OCR or a vision model rather than read
    #: directly from a text layer. Downstream consumers may weight this lower
    #: and the UI must be able to say "this came from a scan".
    extraction_method: str = "text"

    def citation(self, title: str) -> str:
        if self.page_number is not None:
            return f"{title}, p. {self.page_number} ({self.source_uri})"
        if self.section:
            return f"{title}, {self.section} ({self.source_uri})"
        return f"{title} ({self.source_uri})"


def content_hash(text: str) -> str:
    """Stable content hash used for provenance and poisoning detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Document:
    """A source document, before chunking."""

    tenant_id: str
    district_id: str
    document_id: str
    title: str
    document_type: str
    trust_domain: TrustDomain
    data_classification: DataClassification
    authority_level: AuthorityLevel
    acl: AccessControlList
    provenance: Provenance
    status: DocumentStatus = DocumentStatus.ACTIVE
    version: str = "1"
    campus_id: str | None = None
    department_id: str | None = None
    parent_document_id: str | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    security_labels: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class Chunk:
    """The unit of retrieval.

    A chunk inherits its security posture from its document rather than
    carrying an independent one. Letting chunks diverge from their parent is a
    reliable way to leak a paragraph of an HR file out of a document nobody
    thought was reachable.
    """

    chunk_id: str
    document_id: str
    tenant_id: str
    district_id: str
    text: str
    trust_domain: TrustDomain
    data_classification: DataClassification
    authority_level: AuthorityLevel
    acl: AccessControlList
    provenance: Provenance
    title: str = ""
    status: DocumentStatus = DocumentStatus.ACTIVE
    version: str = "1"
    campus_id: str | None = None
    department_id: str | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    ordinal: int = 0

    @classmethod
    def from_document(
        cls, document: Document, chunk_id: str, text: str, ordinal: int = 0,
        provenance: Provenance | None = None,
    ) -> "Chunk":
        """Derive a chunk that cannot accidentally out-scope its document."""
        return cls(
            chunk_id=chunk_id,
            document_id=document.document_id,
            tenant_id=document.tenant_id,
            district_id=document.district_id,
            text=text,
            title=document.title,
            trust_domain=document.trust_domain,
            data_classification=document.data_classification,
            authority_level=document.authority_level,
            acl=document.acl,
            provenance=provenance or document.provenance,
            status=document.status,
            version=document.version,
            campus_id=document.campus_id,
            department_id=document.department_id,
            effective_date=document.effective_date,
            expiration_date=document.expiration_date,
            ordinal=ordinal,
        )

    def validate(self) -> None:
        """Reject a chunk that cannot be safely retrieved. Called at ingest."""
        missing = [
            name
            for name, value in (
                ("chunk_id", self.chunk_id),
                ("document_id", self.document_id),
                ("tenant_id", self.tenant_id),
                ("text", self.text),
                ("provenance.source_uri", self.provenance.source_uri),
                ("provenance.content_hash", self.provenance.content_hash),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"chunk {self.chunk_id!r} missing required: {missing}")
        if not self.acl.allowed_roles and not self.acl.allowed_subjects:
            raise ValueError(
                f"chunk {self.chunk_id!r} has an empty ACL; refusing to index "
                "content that no role and no subject can read -- this is almost "
                "always an ingestion bug, and indexing it risks a later "
                "permissive default making it visible"
            )

    def is_current(self, as_of: date | None = None) -> bool:
        """Freshness check used by corrective RAG."""
        as_of = as_of or datetime.now(timezone.utc).date()
        if self.status is not DocumentStatus.ACTIVE:
            return False
        if self.effective_date and as_of < self.effective_date:
            return False
        if self.expiration_date and as_of > self.expiration_date:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    """A chunk with a retrieval score and the provenance of that score."""

    chunk: Chunk
    score: float
    #: Which retriever produced it, for fusion and for evaluation attribution.
    retriever: str = ""
    rank: int = 0

    def __post_init__(self) -> None:
        if self.score != self.score:  # NaN
            raise ValueError("retrieval score must not be NaN")


def dedupe_by_chunk(results: Sequence[ScoredChunk]) -> list[ScoredChunk]:
    """Keep the highest-scoring occurrence of each chunk."""
    best: dict[str, ScoredChunk] = {}
    for item in results:
        current = best.get(item.chunk.chunk_id)
        if current is None or item.score > current.score:
            best[item.chunk.chunk_id] = item
    return sorted(best.values(), key=lambda s: s.score, reverse=True)
