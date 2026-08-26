#!/usr/bin/env python3
"""Fail the build on secrets, real district data, or weakened security controls.

Three classes of check:

1. **Secrets.** Nothing that looks like a credential may enter the repository.
2. **Real data.** This repository uses synthetic districts only. Content that
   looks like a real student or staff identifier is rejected.
3. **Control erosion.** Patterns that quietly disable a security control --
   an emptied ACL default, a skipped authorization test, a bypass flag -- are
   rejected, because they are how a governed system stops being governed.

The checks are deliberately conservative: they look for shapes, not for a
blocklist of known-bad strings. False positives are resolved by rewording, not
by widening the exception list.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

TEXT_SUFFIXES = {".py", ".json", ".md", ".yml", ".yaml", ".toml", ".cfg", ".txt"}
# Control-erosion patterns are scoped to executable and configuration files.
# Prose that *documents* a rule ("never write `# nosec`") is not a violation of
# it, and a checker that cannot tell the difference trains people to stop
# reading its output.
CODE_SUFFIXES = {".py", ".yml", ".yaml", ".toml", ".cfg"}
SKIP_PARTS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}

SECRET_PATTERNS = [
    (r"(?i)\b(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]",
     "hard-coded credential"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"\bsk-[A-Za-z0-9]{20,}", "provider API key"),
    (r"(?i)DefaultEndpointsProtocol=.*AccountKey=", "Azure storage connection string"),
    (r"(?i)\bAccountKey\s*=\s*[A-Za-z0-9+/]{40,}", "Azure account key"),
]

REAL_DATA_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "value shaped like a US social security number"),
    (r"(?i)\b(student|employee)[_ ]?(ssn|social)\b", "reference to a real identifier field"),
]

CONTROL_EROSION_PATTERNS = [
    (r"(?i)#\s*(nosec|noqa: S1)\b", "suppressed security lint"),
    (r"(?i)\ballow[_-]?all\s*[:=]\s*True", "allow-all flag"),
    (r"(?i)\bbypass[_-]?(auth|authz|authorization|policy)\b", "authorization bypass"),
    (r"(?i)\bverify\s*=\s*False", "disabled TLS verification"),
]

TEST_EROSION_PATTERNS = [
    (r"@pytest\.mark\.skip", "skipped test in the security suite"),
    (r"@pytest\.mark\.xfail", "expected-failure marker in the security suite"),
]


def iter_files():
    for path in sorted(REPO.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.resolve() == SELF:
            continue  # this file necessarily contains the patterns it looks for
        yield path


def main() -> int:
    failures: list[str] = []
    checked = 0

    for path in iter_files():
        checked += 1
        rel = path.relative_to(REPO)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        # Secrets and real data are violations wherever they appear -- a
        # credential pasted into a markdown file is still a credential.
        groups = [
            (SECRET_PATTERNS, "SECRET"),
            (REAL_DATA_PATTERNS, "REAL-DATA"),
        ]
        if path.suffix in CODE_SUFFIXES:
            groups.append((CONTROL_EROSION_PATTERNS, "CONTROL"))
        if str(rel).startswith("tests/security"):
            groups.append((TEST_EROSION_PATTERNS, "TEST"))

        for patterns, label in groups:
            for pattern, description in patterns:
                for match in re.finditer(pattern, text):
                    line = text[: match.start()].count("\n") + 1
                    failures.append(f"[{label}] {rel}:{line}: {description}")

    print(f"hygiene: checked {checked} files")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        print(
            f"\n{len(failures)} hygiene violation(s). "
            "No secrets, no real district data, no silently weakened controls.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
