# OWASP Top 10 for LLM Applications — mapping

Each risk, the platform's control, where it lives, what verifies it, and what
the control does not cover.

---

## LLM01 — Prompt injection

**Control (architectural).** Authorization is computed from the authenticated
principal and never reads text. No code path leads from query content,
document content, or model output to an entitlement.

This is what makes injection unable to escalate privilege: not that the prompt
resists it, but that there is nothing for it to influence.

**Supporting controls.** Retrieved content wrapped in untrusted-content markers
with explicit framing as reference material. Tool calls authorized against the
caller's principal, never the agent's. Model output authorizes nothing.

**Verified by.** `tests/security/test_prompt_injection.py` — 7 injection
strings, plus a test asserting the filter is byte-identical for benign and
hostile queries, plus an indirect-injection test that plants a poisoned
document and confirms it is retrieved as inert content.

**Not covered.** Injection that degrades answer *quality* without escalating
privilege. Prompt-level defences reduce it; the corrective gate and citations
limit the damage. Treat prompt-level mitigation as mitigation, never as the
boundary.

---

## LLM02 — Sensitive information disclosure

**Control.** ACL, tenancy, and trust-domain filtering applied *before*
retrieval; entitlements required beyond role membership for sensitive domains;
in-process re-check as defence in depth; audit records carry identifiers and
hashes, never content.

Model approval constrains where content may be sent independently of what the
user may read — a counselor entitled to a 504 file cannot route it to a model
not approved for student data.

**Verified by.** `test_authorization_boundaries.py` (17 tests) and gold-set
leakage cases, run against a co-located two-tenant index.

**Not covered.** Content ingested with the wrong trust domain.

---

## LLM03 — Supply chain

**Control.** Zero runtime dependencies in the core library. Model and vendor
registries with lifecycle tracking. Preview features excluded from default
routing ([ADR-006](../architecture-decisions/ADR-006-preview-feature-isolation.md)).
Tool registry with declared credential scope. CI hygiene checks.

**Not covered.** Adapter dependencies, once real vendor SDKs are introduced.
The risk rises the moment production adapters ship.

---

## LLM04 — Data and model poisoning

**Control.** Content hashes on every chunk detect post-ingestion tampering.
Provenance records source system and URI. `Chunk.validate()` refuses content
with an empty ACL. Authority ranking limits low-authority influence. Indirect
injection via poisoned content is neutralised by LLM01's architectural control.

**Not covered.** Authorised-but-incorrect content. A district publishing an
incorrect policy gets correct retrieval of an incorrect policy — that is a
records-governance problem, not a retrieval one.

---

## LLM05 — Improper output handling

**Control.** Grounded generation with citations. Corrective gate before
generation.

**Status: partially implemented.** Output validation is a named stage in the
architecture and is **not built** — generation currently ends at the model
gateway. The CSAM output-validation control specified in the policy registry
depends on it.

This is a real gap and is listed in
[`../PROJECT_STATE.md`](../PROJECT_STATE.md).

---

## LLM06 — Excessive agency

**Control.** Read-only tools first; write tools declared without
implementations. Unregistered tool names denied rather than improvised.
Contract invariants refuse roleless tools, audit-disabled tools, and high-risk
writes without human approval. Planners see only tools the caller may invoke.
High-impact decision domains excluded from autonomy entirely. Credentials
scoped per tool.

**Verified by.** `tests/security/test_tool_authorization.py` (10 tests).

---

## LLM07 — System prompt leakage

**Control.** System prompts contain no secrets and no authorization logic.
Extracting the system prompt yields the grounding instruction and nothing of
value, because entitlements live in the policy engine, not the prompt.

This is the right shape of defence: rather than protecting the prompt, ensure
the prompt is not worth protecting.

**Not covered.** The prompt itself is not treated as confidential. That is a
deliberate choice, not an oversight.

---

## LLM08 — Vector and embedding weaknesses

**Control.** Tenant partitioning at the index level. Filter applied during the
scan, so unauthorized chunks are never embedded into a candidate pool.
Embeddings cached by content hash so a tampered chunk does not reuse a vector.
Cosine similarity rejects dimension mismatch loudly rather than producing
silently meaningless scores.

**Corpus statistics are tenant-scoped.** Cross-tenant document frequencies
would let one district's corpus composition influence, and in principle be
inferred from, another district's ranking — a side channel through a component
nobody thinks of as security-relevant.

**Verified by.** `TestCorpusStatistics::test_statistics_are_tenant_scoped`.

---

## LLM09 — Misinformation

**Control.** Grounding with mandatory citations. Authority hierarchy. Freshness
and status checks excluding superseded and expired content. Version-conflict
escalation. Informativeness-weighted relevance so a filler-word match cannot
produce a confident answer. Refusal as a correct outcome.

**Verified by.** Freshness, staleness, conflict, and no-evidence gold cases.

**Not covered.** Semantic contradiction between two current, equal-authority
documents. Conflict detection is structural.

---

## LLM10 — Unbounded consumption

**Control.** Bounded corrective rewrite budget. Cost and tokens computed and
audited per request. Cheapest-approved-model routing.

**Status: partial.** Quotas and rate limits are **not enforced**. Cost is
measured, not capped. Listed in [`../PROJECT_STATE.md`](../PROJECT_STATE.md).

---

## Summary

| Risk | Status |
| --- | --- |
| LLM01 Prompt injection | Strong (escalation); mitigated (quality) |
| LLM02 Sensitive disclosure | Strong |
| LLM03 Supply chain | Strong now; rises with adapters |
| LLM04 Poisoning | Moderate |
| LLM05 Improper output handling | **Gap — output validation not built** |
| LLM06 Excessive agency | Strong (read-only phase) |
| LLM07 System prompt leakage | Strong by design |
| LLM08 Vector weaknesses | Strong |
| LLM09 Misinformation | Strong (structural); gap (semantic) |
| LLM10 Unbounded consumption | **Gap — measured, not capped** |
