# ADR-006 — Preview features must not become silent production dependencies

**Status:** accepted
**Date:** 2026-08-26

## Context

Cloud AI moves fast, and the most interesting capabilities arrive in preview.
Azure AI Search agentic retrieval, new model families, new reranking
endpoints — the temptation to build on them is strong, and often the preview
feature is genuinely the right tool.

The failure mode is not using preview features. It is using them *without
noticing*. A preview API gets used in a spike, the spike becomes the
implementation, and eighteen months later a district's production assistant
depends on an endpoint with no availability commitment, no deprecation notice
period, and terms that may differ from the GA service. Nobody decided this. It
accumulated.

For a school district this is worse than for a startup. The district has a
procurement process that approved a set of services, a security review that
assessed them, and an expectation of multi-year stability.

## Decision

Preview dependencies are **declared, isolated, and visible**.

- `ModelDescriptor.lifecycle` is a required field: `ga`, `preview`,
  `deprecated`, or `retired`.
- **Default routing selects GA only.** `ModelRegistry.select()` excludes
  preview models unless the caller passes `allow_preview=True` explicitly. You
  cannot reach a preview model by accident; you reach it by asking for it.
- `ModelRegistry.preview_models()` reports every preview dependency, so the
  question "what preview features are we on?" has an answer.
- An AI system using a preview capability must record that dependency in its
  registry entry, which surfaces it at approval and at every review.
- Deprecated and retired models are excluded from routing entirely.

The same principle extends beyond models to any preview API: it goes behind an
interface with a GA-based fallback, and the dependency is recorded.

## Consequences

**Good.**

- No silent preview dependencies in production.
- A vendor's preview deprecation is a known-scope change, not an outage with an
  investigation attached.
- Districts can be told accurately which parts of their deployment rest on
  preview terms — a question that comes up in security review and currently has
  no good answer at most vendors.
- Preview features remain usable. This ADR does not ban them; it bans using
  them absent-mindedly.

**Costs.**

- Preview capabilities need a GA fallback path, which is real work and
  sometimes means the fallback is meaningfully worse.
- Lifecycle metadata must be kept current against vendor announcements. Stale
  lifecycle data is worse than none, because it is trusted.
- Occasionally the right engineering answer is the preview feature and the
  ceremony feels like overhead. Accepted: the ceremony is one boolean and a
  registry note.
