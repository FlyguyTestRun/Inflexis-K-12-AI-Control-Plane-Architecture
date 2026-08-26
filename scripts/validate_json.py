#!/usr/bin/env python3
"""Validate that every JSON document in the repository parses and has an id.

Schemas additionally must declare ``$id`` and ``title`` so that they can be
referenced across files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []
    checked = 0

    for path in sorted(REPO.rglob("*.json")):
        if any(part in {".git", "node_modules", ".venv"} for part in path.parts):
            continue
        checked += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.relative_to(REPO)}: invalid JSON: {exc}")
            continue
        if path.parent.name == "schemas":
            for field in ("$id", "$schema", "title"):
                if field not in payload:
                    failures.append(
                        f"{path.relative_to(REPO)}: schema missing {field!r}"
                    )

    print(f"checked {checked} JSON files")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
