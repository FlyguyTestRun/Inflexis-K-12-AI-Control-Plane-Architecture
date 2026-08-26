"""Inflexis K-12 AI Control Plane.

A governed AI control plane for Texas K-12 school districts.

The package is organised around the six architectural planes described in
``docs/architecture.md``:

    governance  -- Plane 1: AI inventory, use-case registry, risk, approval
    authz       -- Plane 2: identity, tenancy, RBAC/ABAC, document ACL
    contracts   -- cross-plane data + interface contracts
    retrieval   -- Plane 4: hybrid / corrective / graph / agentic retrieval
    models      -- Plane 5: model gateway and provider abstractions
    tools       -- Plane 6: tool registry and action governance
    audit       -- cross-cutting audit + provenance
    evaluation  -- cross-cutting evaluation harness

Nothing in this package may talk to a model vendor SDK directly; all inference
flows through :mod:`inflexis.models`.
"""

__version__ = "0.1.0"
