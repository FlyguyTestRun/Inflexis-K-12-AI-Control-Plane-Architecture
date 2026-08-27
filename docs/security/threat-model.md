# Threat model

Scoped to the AI control plane. Ordered by expected damage to a district, not
by exploit sophistication.

Each threat records: what it is, what it costs the district, the control, where
that control lives, and — where it matters — what the control does **not**
cover.

---

## Assets

1. Student education records (FERPA)
2. Personnel records
3. Legally privileged material
4. Security credentials and configuration
5. District decision integrity — the correctness of answers people act on
6. Tenant isolation between districts

---

## T1 — Cross-tenant data leakage

**Damage:** catastrophic. One district reading another's student data ends the
company, not just the contract.

**Vector:** missing tenant predicate, a shared index without partitioning, a
cache keyed without tenant, statistics computed across tenants.

**Controls**
- `tenant_id` is a mandatory predicate on every retrieval; no code path widens
  it. `PolicyEngine.authorize_retrieval` rejects a principal whose tenant does
  not match the engine's.
- `InMemoryIndex` partitions by tenant so a missing predicate cannot scan
  another district's content.
- Corpus statistics are computed **per tenant** — cross-tenant document
  frequencies would let one district's corpus composition influence, and be
  inferred from, another's ranking.
- Tools reject `tenant_scope` other than `single` or `none`.

**Verified by:** `TestTenantIsolation` (4 tests), run against a co-located
two-tenant index.

---

## T2 — Unauthorized retrieval within a tenant

**Damage:** severe. A teacher reading HR grievances or a 504 file is a
reportable incident.

**Vector:** a retriever added without a filter; a chunk whose ACL diverged from
its document; role membership treated as sufficient for sensitive data.

**Controls**
- Authorization precedes retrieval and cannot be skipped — `AuthorizedQuery` is
  unforgeable ([ADR-003](../architecture-decisions/ADR-003-authorization-before-retrieval.md)).
- Chunks inherit ACLs from their document via `Chunk.from_document`; they
  cannot out-scope it.
- Sensitive domains require an explicit permission beyond role membership.
- In-process re-check drops anything the backend should not have returned,
  audited at `SECURITY` severity.

**Verified by:** `test_authorization_boundaries.py` (17 tests) and gold-set
leakage cases.

**Not covered:** content ingested with the wrong trust domain. Ingestion
governance, not retrieval, owns that.

---

## T3 — Prompt injection (direct and indirect)

**Damage:** high if it escalates privilege; moderate if it only degrades
answers.

**Vector:** a user typing "ignore previous instructions"; an attacker planting
instructions in a document, a web page, or tool output that later enters
context.

**Controls**
- **The primary control is architectural:** authorization is computed from the
  principal and never reads text. There is no code path from query or document
  content to an entitlement, so injection cannot widen access regardless of
  phrasing.
- Retrieved content is wrapped in untrusted-content markers with an explicit
  instruction that it is reference material, not instructions.
- Tool calls are authorized against the caller's principal, never the agent's.
- Model output is untrusted and authorizes nothing.

**Verified by:** `test_prompt_injection.py` — 7 injection strings × 2
assertions, plus an indirect-injection test that plants a poisoned document in
the corpus and confirms it is retrieved as inert content.

**Not covered:** injection that degrades answer *quality* without escalating
privilege. Prompt-level mitigations reduce it; grounding, citations, and the
corrective gate limit the damage. Treat prompt-level defences as mitigation,
never as the boundary.

---

## T4 — Confabulation presented as district policy

**Damage:** high and frequently underestimated. A staff member acting on
invented policy — or on repealed policy stated as current — causes real harm,
and it is the failure most likely to end a pilot.

**Vector:** thin evidence, stale evidence, conflicting sources, or a question
the corpus does not address.

**Controls**
- Corrective gate: relevance, freshness, authority, conflict, sufficiency
  checks before generation.
- Relevance is weighted by term informativeness, so a query matching only
  filler words cannot clear the gate.
- Superseded and expired content is excluded from retrieval by status and date.
- Same-authority version conflicts escalate rather than silently picking a
  winner.
- Every answer carries citations with page or section provenance.

**Verified by:** freshness, staleness, conflict, and no-evidence cases in the
gold set and `test_hybrid_retrieval.py`.

**Not covered:** two documents that contradict each other in prose without a
version or authority difference. Conflict detection is structural, not
semantic — stated as a known limitation in
[`../PROJECT_STATE.md`](../PROJECT_STATE.md).

---

## T5 — Excessive agency

**Damage:** high once write tools exist. An agent sending email or mutating a
student record on a hallucinated premise.

**Vector:** an over-permissioned tool; an agent inventing a tool name; a
high-risk write reachable without approval.

**Controls**
- Phase 3 starts read-only. Write tools are declared without implementations.
- Unregistered tool names are denied, not improvised.
- Contract invariants refuse roleless tools, audit-disabled tools, and
  high-risk writes without human approval.
- Planners see only tools the caller may invoke.
- High-impact decision domains are excluded from autonomy entirely.

**Verified by:** `test_tool_authorization.py` (10 tests).

---

## T6 — Data poisoning

**Damage:** moderate to high. Corrupted answers with district authority
attached.

**Vector:** malicious or erroneous content entering the corpus.

**Controls**
- Content hashes on every chunk detect tampering after ingestion.
- Provenance records source system and URI for every piece of evidence.
- Authority ranking limits the influence of low-authority sources.
- ACL validation at index time refuses content nobody can read.
- Indirect injection via poisoned content is neutralised by T3's architectural
  control.

**Not covered:** authorised-but-wrong content. A district that publishes an
incorrect policy gets correct retrieval of an incorrect policy.

---

## T7 — Sensitive disclosure through the model provider

**Damage:** high, and often invisible until a contract review.

**Vector:** confidential content routed to a model not approved for it, or to a
vendor whose terms permit training on submitted data.

**Controls**
- `approved_trust_domains` gates routing independently of user entitlement.
- The registry refuses to construct a descriptor combining
  `vendor_may_train_on_data` with any non-public domain.
- Routing fails loudly when no approved model covers the content, rather than
  falling back.
- Audit records the model and the trust domains it received.

---

## T8 — Supply chain

**Damage:** varies; potentially total.

**Vector:** a compromised dependency, an unvetted model, a preview API changing
behaviour under production traffic.

**Controls**
- Zero runtime dependencies in the core library.
- Model and vendor registries with lifecycle tracking.
- Preview features excluded from default routing
  ([ADR-006](../architecture-decisions/ADR-006-preview-feature-isolation.md)).
- Repository hygiene checks in CI.

---

## T9 — Audit evasion and control erosion

**Damage:** moderate directly; severe as an enabler, because it removes the
evidence that anything else went wrong.

**Vector:** a tool registered with audit disabled; a skipped security test; a
suppressed lint; an ACL default quietly loosened.

**Controls**
- `audit_required` is a `const: true` in the schema and a contract invariant.
- `scripts/check_repository_hygiene.py` fails the build on suppressed security
  lint, allow-all flags, authorization bypass identifiers, disabled TLS
  verification, and skip/xfail markers inside `tests/security`.
- Audit records exclude document content, so the audit log is not itself a
  disclosure route.

---

## T10 — Unbounded consumption

**Damage:** low to moderate. Budget exhaustion; degraded service.

**Vector:** runaway agent loops, expensive queries at scale, retry storms.

**Controls**
- Corrective rewrite budget is bounded and enforced by the loop.
- Cost per request is computed and audited.

**Not covered:** quota and rate-limit *enforcement* is not implemented. Cost is
measured, not capped. Recorded in
[`../PROJECT_STATE.md`](../PROJECT_STATE.md) as a gap.

---

## Residual risk summary

| Threat | Residual | Why |
| --- | --- | --- |
| T1 Cross-tenant | Low | Structural, multiply enforced, tested co-located |
| T2 Unauthorized retrieval | Low | Structural; residual is ingestion mislabelling |
| T3 Injection → escalation | Low | No text-to-entitlement path exists |
| T3 Injection → quality | **Medium** | Mitigated, not eliminated |
| T4 Confabulation | Medium | Gated; semantic contradiction undetected |
| T5 Excessive agency | Low *now* | Read-only phase; rises when writes ship |
| T6 Poisoning | Medium | Detects tampering, not authorised error |
| T7 Provider disclosure | Low | Gated; residual is vendor-contractual |
| T8 Supply chain | Low | Zero deps; rises with adapters |
| T9 Audit evasion | Low | CI-enforced |
| T10 Consumption | **Medium** | Measured but not capped |
