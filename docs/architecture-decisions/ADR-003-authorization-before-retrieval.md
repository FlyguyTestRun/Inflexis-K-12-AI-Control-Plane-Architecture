# ADR-003 — Authorization happens before retrieval

**Status:** accepted
**Date:** 2026-08-26

## Context

There are two ways to build access control into a RAG system.

**The wrong one**, which is common because it is easy:

```
search everything → send everything to the model → instruct the model
                                                    not to reveal restricted data
```

**The right one:**

```
identity → tenant → roles/attributes → entitlements → policy
        → retrieval filter → search → rerank → authorized context → model
```

The first architecture is unacceptable for K-12 for reasons that are worth
stating plainly rather than assuming:

1. **The model is not an access control mechanism.** It is a text generator
   that can be argued with. Prompt injection defeats instruction-based
   restriction reliably, and "reliably" is the operative word when the data is
   student records.
2. **Unauthorized content in the context window is already a disclosure.** It
   sits in provider logs, in traces, in any caching layer. Whether the model
   chose to quote it is not the question.
3. **It is unauditable.** "The model was told not to" is not an answer to a
   parent, a board member, or counsel.

## Decision

No unauthorized document or chunk enters model context. Ever.

Authorization is computed from the **authenticated principal** before any
retrieval occurs, and produces a `RetrievalFilter` that every backend must
apply inside its own query.

This is enforced structurally, not by convention:

- `Retriever.retrieve()` accepts an `AuthorizedQuery`.
- `AuthorizedQuery.__post_init__` raises `PermissionError` unless the caller
  holds a module-private capability token.
- Only a `PolicyDecisionPoint` holds that token.

A developer therefore **cannot call a retriever without proof that
authorization happened**, and the filter travels with the query rather than
being passed alongside it and forgotten.

Three further properties:

- **Authorization never reads the prompt.** Entitlements are computed from the
  principal alone. A test asserts that the filter is byte-identical for a
  benign query and a hostile one. This is what makes prompt injection unable
  to escalate: there is no code path from query text to entitlement.
- **Defence in depth.** The pipeline re-checks every returned chunk against the
  filter in process. A non-empty drop list means a backend adapter failed to
  apply the filter, which is audited at `SECURITY` severity as an incident —
  not logged as a warning. A retriever that relies on this re-check is broken,
  because unauthorized rows were already read out of the datastore.
- **Tenant is a hard predicate.** No configuration, role, or policy widens a
  query across tenants. There is no platform-admin bypass: a platform
  administrator administers the platform, not every district's student records.

## Consequences

**Good.**

- Unauthorized content cannot reach a model, a log, or a provider.
- Prompt injection cannot escalate privilege, because there is no path from
  text to entitlement.
- Every decision is auditable as a `PolicyDecision` with the rules that fired.
- Adding a retriever cannot silently bypass authorization.

**Costs.**

- Retrieval backends must support filter pushdown. A backend that cannot filter
  server-side is not usable, which narrows vendor choice.
- Recall is genuinely lower for restricted users. That is correct behaviour,
  but it must be explained during onboarding or it reads as a bug.
- Cross-tenant analytics require a separate, explicitly governed path.
- The capability-token pattern is unusual and needs explaining to new
  engineers. That cost is paid once; the alternative is paid at every code
  review, forever.

## Verification

`tests/security/test_authorization_boundaries.py` (17 tests) and
`tests/security/test_prompt_injection.py` run against an index containing two
districts, because one search service serving many districts is the realistic
deployment and the only one in which leakage is possible.
