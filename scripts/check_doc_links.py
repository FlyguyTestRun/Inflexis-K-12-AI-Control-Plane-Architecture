#!/usr/bin/env python3
"""Verify that internal documentation links resolve.

Documentation is a deliverable here: a district's security reviewer and a new
engineer both navigate by these links. A broken cross-reference in a governance
mapping costs more trust than a broken import, because the reader cannot tell
whether the target is missing or the claim is unsupported.

External URLs are not fetched -- their verification status is tracked in
docs/governance/source-registry.md instead.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def main() -> int:
    broken: list[str] = []
    checked = 0

    for markdown in sorted(REPO.rglob("*.md")):
        if ".git" in markdown.parts:
            continue
        for match in LINK.finditer(markdown.read_text(encoding="utf-8")):
            target = match.group(2)
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path = target.split("#")[0]
            if not path:
                continue
            checked += 1
            if not (markdown.parent / path).resolve().exists():
                rel = markdown.relative_to(REPO)
                broken.append(f"{rel}: [{match.group(1)}] -> {target}")

    print(f"checked {checked} internal documentation links")
    for item in broken:
        print(f"FAIL broken link {item}", file=sys.stderr)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
