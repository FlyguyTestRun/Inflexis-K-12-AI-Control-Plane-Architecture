"""Synthetic district fixtures.

Everything here is fabricated. No real student, personnel, or district data
appears in this repository -- see ``docs/security/trust-boundaries.md`` and the
CI check in ``.github/workflows/ci.yml``.
"""

from .acme_isd import (
    ACME,
    BRAVO,
    build_acme_index,
    build_two_tenant_index,
    principals,
)

__all__ = [
    "ACME",
    "BRAVO",
    "build_acme_index",
    "build_two_tenant_index",
    "principals",
]
