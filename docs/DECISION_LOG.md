# Decision log

Chronological record of decisions taken during implementation. Architectural
decisions of lasting consequence graduate to an ADR in
[`architecture-decisions/`](architecture-decisions/); this log captures
everything, including the smaller calls and the reversals.

Entries are append-only. A decision that turned out to be wrong is superseded
by a later entry, not edited away.

---

## D-001 — Treat the repository as greenfield

**Date:** 2026-08-26 · **Status:** accepted

Repository inspection found one 45-byte README and nothing else. Rather than
manufacture a conflict list to satisfy the handoff's reconciliation step,
[`ARCHITECTURE_CONFLICT_REPORT.md`](ARCHITECTURE_CONFLICT_REPORT.md) records a
greenfield finding and documents the three places where the handoff assumes
prior work (notably MAOP) that does not exist.

---

## D-002 — Zero runtime dependencies in the core library

**Date:** 2026-08-26 · **Status:** accepted

The contracts, governance, authorization, and retrieval layers use only the
standard library. Vendor SDKs are confined to optional adapter extras.

**Why.** Three reasons, in order of weight. It keeps the security-critical
layers auditable by a district's own reviewers without a dependency review.
It lets the whole test suite run in CI and on a phone-driven cloud session with
no cloud credentials. And it makes ADR-005's vendor-neutrality claim structural
rather than aspirational — you cannot accidentally couple to a vendor whose SDK
you have not imported.

**Cost.** A hand-rolled BM25 and an in-memory index that production will
replace. Accepted: they are reference implementations whose purpose is to pin
the contract, not to serve traffic.

---

## D-003 — Make `AuthorizedQuery` unforgeable

**Date:** 2026-08-26 · **Status:** accepted · **See** [ADR-003](architecture-decisions/ADR-003-authorization-before-retrieval.md)

Retrievers accept an `AuthorizedQuery`, which cannot be constructed by calling
code — only a policy decision point holding a module-private capability token
can mint one.

**Why.** "Authorize before retrieving" is the kind of rule that decays. Someone
adds a retriever, forgets the filter, and nothing complains until a teacher
sees an HR file. Making the requirement structural means a developer *cannot*
call a retriever without proof that a policy decision happened, and the filter
travels with the query rather than being passed alongside it and dropped.

---

## D-004 — Fail-closed ACLs

**Date:** 2026-08-26 · **Status:** accepted

An `AccessControlList` with no allowed roles and no allowed subjects permits
nobody, and `Chunk.validate()` refuses to index such content.

**Why.** The opposite default — empty means unrestricted — is the more common
convention and is wrong here. The failure mode of a tight default is a support
ticket. The failure mode of a loose default is a FERPA incident. Refusing to
index rather than silently indexing unreadable content also catches the
ingestion bug that produced the empty ACL in the first place.

---

## D-005 — Separate trust domain, data classification, and authority

**Date:** 2026-08-26 · **Status:** accepted

Three orthogonal axes rather than one sensitivity scale.

**Why.** They answer different questions: where content lives (index
partitioning), how carefully it must be handled, and how much it should be
believed. A public web page and a board policy may be equally non-sensitive
while carrying wildly different authority. Conflating them produces a system
that either over-restricts public policy or under-protects a low-authority
document that happens to contain student names.

---

## D-006 — Model approval constrains where content may be *sent*

**Date:** 2026-08-26 · **Status:** accepted

`ModelDescriptor.approved_trust_domains` gates routing independently of the
caller's entitlements. A counselor entitled to read student records still
cannot cause that content to reach a model not approved for it.

**Why.** Entitlement and data egress are different questions that are easy to
collapse into one. The registry also refuses to construct a descriptor that
combines `vendor_may_train_on_data` with any non-public approved domain,
because that combination is a data-protection incident waiting for a
misconfiguration.

---

## D-007 — HB 2818 is a product capability, not a compliance control

**Date:** 2026-08-26 · **Status:** accepted · **Supersedes** the handoff's §21 framing

Modernisation measurement is implemented in full but recorded with
`district_applicability: does_not_apply`.

**Why.** HB 2818 creates an AI division within DIR for state legacy-system
modernisation. It is an agency-structure bill and does not, on the available
evidence, impose a measurement duty on school districts. Districts still need
to demonstrate that AI improved a process — that is a procurement and
credibility argument, and a good one. Labelling it compliance would be exactly
the overclaiming the handoff's §18 forbids.

---

## D-008 — Authority gate is opt-in per use case

**Date:** 2026-08-26 · **Status:** accepted · **Revises** an earlier
implementation in this same pass

Initially the corrective checker required authority at or above district
handbook by default, following §8 and §15 literally.

**What broke.** Three access tests failed: HR could not retrieve the
compensation schedule, a counselor could not retrieve a 504 case file, and a
teacher could not retrieve their own campus bell schedule. All three are
department- or campus-level documents ranking below the handbook threshold —
and all three are the *authoritative* source for the question asked.

**Resolution.** Authority always weights ranking. The authority *gate* is
enabled per use case by the router for policy and compliance questions.
Tested both ways.

---

## D-009 — Authority and freshness amplify relevance, never create it

**Date:** 2026-08-26 · **Status:** accepted · **Revises** an earlier
implementation in this same pass

The heuristic reranker originally scored
`coverage + w_a·authority + w_f·freshness`.

**What broke.** A nonsense query cleared the corrective gate. The additive
bonuses act as a score floor of roughly 0.5 for any current, authoritative
document, regardless of whether it addresses the question. The gate was
effectively disabled.

**Resolution.** `coverage × (1 + w_a·authority + w_f·freshness)`. A document
that does not address the question scores zero no matter how authoritative it
is. Pinned by
`tests/retrieval/test_hybrid_retrieval.py::TestRelevanceGate::test_authority_does_not_manufacture_relevance`.

---

## D-010 — Weight relevance by term informativeness, scoped per tenant

**Date:** 2026-08-26 · **Status:** accepted

Running the gold set exposed a second relevance failure that D-009 did not fix:
"What is the district policy on interplanetary field trips?" produced a
confident answer citing unrelated board policy.

**Cause.** Coverage counted every query term equally. `the`, `district`, and
`policy` match most of the corpus; `interplanetary` matches nothing. Enough
filler terms matched to clear the floor.

**Resolution.** Coverage is weighted by term informativeness (an IDF-style
weight), so an unmatched rare term dominates. Corpus statistics are computed
**per tenant** — cross-tenant document frequencies would let one district's
corpus composition influence, and in principle be inferred from, another
district's ranking. That is a side channel through a component nobody thinks of
as security-relevant, which is what makes it worth closing early.

---

## D-011 — The corrective loop must reach a terminal verdict

**Date:** 2026-08-26 · **Status:** accepted

`pipeline.run()` executes one pass; `pipeline.answer()` drives the corrective
loop until the verdict is terminal.

**Why.** The checker can return `REWRITE_QUERY`, which is a provisional
instruction, not an answer. Returning it to a caller that has no rewriter
leaves the caller holding a verdict it cannot act on — and the tempting fix is
to treat "not a refusal" as "go ahead and answer". `answer()` exhausts the
budget and converts the provisional verdict into refuse or escalate.

A rewritten query is re-authorized through the decision point rather than
reusing the existing filter. Our engine computes the filter independently of
query text, but that is a property of *this* engine, not a guarantee of the
`PolicyDecisionPoint` protocol.

---

## D-012 — Co-locate tenants in the test index

**Date:** 2026-08-26 · **Status:** accepted

Security tests run against an index containing both Acme ISD and Bravo ISD.

**Why.** One search service serving many districts is the realistic deployment
and the only configuration in which leakage is possible. Testing isolation with
one tenant per index proves nothing except that separate indexes are separate.

---

## D-013 — `blake2b` rather than `md5` for feature hashing

**Date:** 2026-08-26 · **Status:** accepted

The offline embedding provider hashes tokens into vector buckets. This is
feature hashing, not a security primitive, and `md5` would be functionally
fine.

**Why change it.** Shipping `md5` in a product sold to school districts on its
security posture invites a finding in every scanner the district runs, and
answering "it is not used for security" in a procurement review costs more than
the change did. The alternative — suppressing the lint with `# nosec` — is
itself flagged by this repository's own hygiene check as control erosion.

---

## D-014 — Enum migration to `StrEnum`

**Date:** 2026-08-26 · **Status:** accepted

`class X(str, Enum)` became `class X(StrEnum)` throughout the contracts.

**Why.** Python 3.11 is the floor, `StrEnum` is the idiom, and it gives clean
serialization without the mixed-inheritance subtleties. Mechanical change, no
behavioural difference in this codebase; recorded because it touched every
contract module.
