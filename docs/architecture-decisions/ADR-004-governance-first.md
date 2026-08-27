# ADR-004 — Governance is a first-class architectural component

**Status:** accepted
**Date:** 2026-08-26

## Context

AI governance is usually implemented as documentation: a policy PDF, a
spreadsheet inventory, an annual review meeting. This fails in a specific way —
the spreadsheet drifts. Someone stands up a pilot, it becomes load-bearing,
nobody updates the inventory, and eighteen months later the district cannot
answer what AI is running or who approved it.

For a Texas district this is no longer merely embarrassing. SB 1964 moves in
the direction of AI inventory and risk assessment obligations for public
entities, HB 3512 reaches school district employees on training, and TRAIGA
constrains certain uses outright. The exact applicability to an ISD is a legal
question this repository does not answer (see ADR-004's companion,
[`../governance/texas-applicability.md`](../governance/texas-applicability.md)),
but the direction is not in doubt.

## Decision

Governance is **on the request path**, not beside it.

- **The AI registry is a gate.** `AIRegistry.assert_may_serve()` rejects
  traffic carrying an unregistered, unapproved, prohibited, or
  not-yet-deployed `ai_system_id`. An AI system that is not in the inventory
  cannot serve. The inventory cannot drift from reality because reality is
  gated on the inventory.
- **Risk classification has teeth.** `AISystemRecord` refuses construction if a
  prohibited system is marked deployed, or if a heightened-scrutiny system has
  no documented human-oversight mechanism. These are contract invariants, not
  review checklist items.
- **Prohibited-use screening happens at registration**, before anything is
  built, via `governance/texas/policy-controls.json`.
- **Rejected systems stay in the registry.** The synthetic Acme ISD inventory
  includes a rejected composite student-risk-scoring system, retained as
  evidence that the screening control fired. Deleting rejected entries destroys
  the record that governance worked.
- **Applicability is data, never a code assertion.** Every requirement row
  carries a citation URL, an applicability value, a verification status, and a
  legal-review flag. The default for anything not determinable from statute
  text alone is `requires_legal_review`.

## The line this repository will not cross

The platform implements **engineering controls**. It does not assert legal
compliance, and it must never imply that installing software makes a district
compliant with any statute or rule.

This is not lawyerly hedging; it is load-bearing. A district that believes the
software has handled compliance will not do the legal review that only its
counsel can do. A test enforces the boundary:
`test_unverified_rows_require_legal_review_or_are_not_asserted` fails the build
if a row derived only from secondary sources claims a requirement definitively
applies.

## Consequences

**Good.**

- "What AI is running here?" has a computed answer.
- Governance metrics (approved, unapproved, overdue review, heightened
  scrutiny, training completion) are queryable rather than assembled by hand.
- Evidence for a review is a query, not an archaeology project.
- An approval with no review date counts as overdue: "approved once in 2026" is
  not a governance posture.

**Costs.**

- Registering a use case is friction, deliberately. Teams will want to skip it.
- The registry becomes a dependency of the request path, so its availability
  matters.
- Applicability rows require genuine legal review to become useful; the
  platform ships them unresolved and says so.
