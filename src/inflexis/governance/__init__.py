"""Plane 1: governance.

Governance is not a reporting layer bolted on after the fact. The registry in
this package is on the request path: an AI system that is not registered and
approved cannot serve production traffic.
"""

from .registry import AIRegistry, GovernanceError
from .applicability import ApplicabilityMatrix, load_matrix

__all__ = ["AIRegistry", "GovernanceError", "ApplicabilityMatrix", "load_matrix"]
