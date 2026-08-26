"""Governance applicability matrices.

The repository must never state a legal conclusion in its own voice. What it
can do -- and what this module does -- is carry a *reviewable* mapping from a
cited requirement to the engineering control that would satisfy it, with an
explicit applicability value that a district's counsel sets.

The default for anything not determinable from the statute text alone is
``REQUIRES_LEGAL_REVIEW``. That default is the honest one, and it is load
bearing: it keeps the platform from implying that installing software makes a
district compliant.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

from ..contracts.governance import Applicability, RequirementMapping

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MATRIX_DIR = REPO_ROOT / "governance" / "texas"


class ApplicabilityMatrix:
    """A set of requirement mappings for one jurisdiction or framework."""

    def __init__(self, name: str, rows: Iterable[RequirementMapping] = ()) -> None:
        self.name = name
        self._rows: list[RequirementMapping] = list(rows)

    def __iter__(self) -> Iterator[RequirementMapping]:
        return iter(self._rows)

    def __len__(self) -> int:
        return len(self._rows)

    def add(self, row: RequirementMapping) -> None:
        self._rows.append(row)

    def by_id(self, requirement_id: str) -> RequirementMapping | None:
        return next(
            (r for r in self._rows if r.requirement_id == requirement_id), None
        )

    def requiring_legal_review(self) -> list[RequirementMapping]:
        return [
            r
            for r in self._rows
            if r.legal_review_required
            or r.district_applicability is Applicability.REQUIRES_LEGAL_REVIEW
        ]

    def unimplemented(self) -> list[RequirementMapping]:
        """Rows whose control has no implementation reference yet."""
        return [r for r in self._rows if not r.implemented_by.strip()]

    def coverage(self) -> dict[str, int]:
        return {
            "requirements": len(self._rows),
            "implemented": len(self._rows) - len(self.unimplemented()),
            "awaiting_legal_review": len(self.requiring_legal_review()),
        }


def load_matrix(path: str | Path) -> ApplicabilityMatrix:
    """Load a matrix from the JSON files under ``governance/``."""
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        RequirementMapping(
            requirement_id=row["requirement_id"],
            source=row["source"],
            statute_or_rule=row["statute_or_rule"],
            citation_url=row["citation_url"],
            actor=row["actor"],
            summary=row["summary"],
            district_applicability=Applicability(row["district_applicability"]),
            use_case_applicability=row.get("use_case_applicability", ""),
            required_control=row.get("required_control", ""),
            implemented_by=row.get("implemented_by", ""),
            evidence=row.get("evidence", ""),
            legal_review_required=row.get("legal_review_required", True),
            verification_status=row.get("verification_status", "unverified"),
            notes=row.get("notes", ""),
        )
        for row in payload["requirements"]
    ]
    return ApplicabilityMatrix(payload.get("name", path.stem), rows)
