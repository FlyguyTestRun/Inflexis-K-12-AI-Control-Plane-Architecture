# ADR-001 — A governed AI control plane, not an AI application

**Status:** accepted
**Date:** 2026-08-26
**Deciders:** CTO / Lead AI Architect

## Context

The obvious way to sell AI to a school district is to build a chatbot over
district documents. It demos well and it is quick.

It also fails in a specific, predictable way. The district ends up with an AI
*application*: one assistant, one corpus, one set of permissions baked into
whoever built it. When the second use case arrives — IT support, HR
self-service, a campus assistant — the district builds a second application
with its own corpus, its own permission model, and its own audit story. Within
a year the district has an uncontrolled collection of AI applications, no
inventory, no consistent authorization, and no way to answer "what AI is
running here and who approved it?"

That question is not hypothetical. It is the first question in any AI
governance review, and increasingly the first question from the state.

The handoff refers to MAOP becoming the control/orchestration layer. No MAOP
code exists in this repository (see
[`../ARCHITECTURE_CONFLICT_REPORT.md`](../ARCHITECTURE_CONFLICT_REPORT.md)),
so this ADR defines the control plane from first principles rather than
repurposing an existing component.

## Decision

Build a **control plane** that AI capabilities plug into, rather than an AI
application.

The control plane owns identity, tenancy, authorization, policy, the model
gateway, the model and tool registries, audit, observability, and FinOps. An
AI use case is a *registered entry* in that control plane, not a separate
system with its own copy of these concerns.

Concretely:

- Every AI system has an entry in the AI registry, and
  `AIRegistry.assert_may_serve()` gates production traffic on it.
- Every retrieval passes through one policy decision point.
- Every inference passes through one model gateway.
- Every tool invocation passes through one authorizing registry.
- Every one of the above emits audit records with a common schema.

Adding a second use case means adding a registry entry and a configuration, not
a second stack.

## Consequences

**Good.**

- One district, many governed use cases, one audit trail.
- One platform, many districts (see ADR-005 on tenancy and vendor neutrality).
- The governance questions have answers that are computed rather than
  assembled by hand for each review.
- A new use case inherits every security control by construction.

**Costs, honestly.**

- The first use case is meaningfully more expensive than a chatbot would have
  been. The control plane must exist before anything ships.
- There is more to explain in a sales conversation than "we built you a
  chatbot."
- Contracts must be stable early, because everything binds to them. Getting the
  document and chunk contracts wrong is expensive to correct later.

**Rejected alternative: build the chatbot first, extract the platform later.**
This is the standard advice and it is usually right. It is wrong here because
the extraction never happens on a security boundary. Authorization designed
into a single-corpus assistant does not generalise to seven trust domains and
multiple tenants; it gets retrofitted, and retrofitted authorization is how
student records leak. The control plane is the part that cannot be added
afterwards.

## Related

ADR-003 (authorization before retrieval), ADR-004 (governance first).
