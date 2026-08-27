# CLAUDE.md — working in this repository

Guidance for Claude Code and for any engineer new to the codebase. Read this
before changing anything under `src/inflexis/authz/`, `contracts/`, or
`governance/`.

---

## What this is

A governed AI control plane for Texas K-12 school districts. Not a chatbot, not
a RAG demo. The security and governance properties are the product.

Orientation: [`README.md`](README.md) → [`docs/architecture.md`](docs/architecture.md)
→ [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md).

---

## Rules that are not negotiable

These exist because the failure modes are severe and, in a school district,
reportable.

1. **Never weaken an authorization control to make a test pass.** If a test
   fails because authorization is denying something, the answer is either that
   the test's expectation is wrong or the entitlement model needs a deliberate,
   documented change. It is never "loosen the default."
2. **Never introduce real student, personnel, or district data.** Every fixture
   is synthetic. CI enforces this.
3. **Never commit secrets.** No keys, tokens, connection strings, or
   credentials. CI enforces this.
4. **Never bypass governance for convenience.** No `allow_all`, no admin
   bypass, no "just for testing" flag that survives the branch.
5. **Never let query text, document content, or model output influence an
   authorization decision.** This is the property that makes prompt injection
   unable to escalate privilege. It is worth more than any feature.
6. **Never state a legal conclusion in the repository's own voice.** Governance
   mappings carry citations, applicability values, and verification status.
   Applicability is counsel's determination, not ours.
7. **Never suppress a security lint** (`# nosec`, `# noqa: S...`). The hygiene
   check treats suppression as control erosion and fails the build. Fix the
   code instead.

---

## Before you change something

**Inspect first.** Search before opening large files. Read the relevant ADR
before changing what it decided.

**Check whether an ADR governs it.** Six ADRs cover the control plane, hybrid
retrieval, authorization ordering, governance, vendor neutrality, and preview
isolation. Changing one of those decisions means writing an ADR, not editing
code and moving on.

**Add to the decision log.** [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) is
append-only. A decision that turned out wrong is superseded by a later entry,
not edited away.

---

## Architectural invariants

Break these and the system stops being what it claims to be.

| Invariant | Enforced by |
| --- | --- |
| Authorization precedes retrieval | `AuthorizedQuery` is unforgeable — only a PDP holds the capability token |
| Tenant is a hard predicate | `PolicyEngine` rejects cross-tenant principals; index partitions by tenant |
| ACLs fail closed | `AccessControlList.permits` requires an explicit grant; `Chunk.validate` refuses empty ACLs |
| Chunks cannot out-scope their document | `Chunk.from_document` derives the security posture |
| Sensitive domains need permission, not just role | `PolicyEngine.allowed_domains` strips domains whose required permissions are unmet |
| F and G domains are unreachable by general grants | `RESTRICTED_BY_DEFAULT` |
| Tools declare full posture or cannot register | `ToolDescriptor.__post_init__` |
| Audit cannot be disabled | `audit_required` invariant and `const: true` in schema |
| Audit records exclude document content | Reviewed at every change to `AuditEvent` |
| Model approval constrains egress | `ModelRegistry.select` matches `approved_trust_domains` |
| Unregistered AI systems cannot serve | `AIRegistry.assert_may_serve` |

---

## Testing

```bash
pytest -q                      # all 91
pytest tests/security -q       # authorization boundaries
pytest tests/governance/test_evaluation.py -q   # gold set, release gate
```

**Any change touching authorization, retrieval filtering, tenancy, or tool
registration requires a corresponding security test.** Not a unit test of the
new code — a test of the boundary it could break.

Security tests run against a **co-located two-tenant index**, because one
search service serving many districts is the realistic deployment and the only
configuration in which leakage is possible.

---

## Style

Match the surrounding code. Specifically:

- **Comments explain why, not what.** The codebase comments decisions and
  non-obvious trade-offs, not mechanics. If a comment restates the line below
  it, delete it.
- **Docstrings on modules and public classes** state what the component is for
  and what failure it prevents.
- Type hints throughout. `from __future__ import annotations`.
- Frozen dataclasses for contracts; `slots=True` where sensible.
- No runtime dependencies in the core library. Vendor SDKs go in optional
  extras, and only `inflexis.models` may import a model vendor SDK.

---

## Common tasks

**Adding a retriever.** Implement `Retriever`. It receives an `AuthorizedQuery`
and must apply `query.filter` *inside* the backend query. A retriever that
fetches then filters has already read unauthorized rows out of the datastore —
the pipeline's re-check will not save you, it will just tell you afterwards.

**Adding a tool.** Write the `ToolDescriptor` first. If you cannot fill in risk
level, credential scope, reversibility, and rollback, the tool is not ready.
Start read-only.

**Adding a governance requirement.** Add a row to the applicability matrix with
a citation URL and a verification status. Default `district_applicability` to
`requires_legal_review` unless you have primary-source evidence.

**Changing a threshold.** Thresholds are calibrated, not chosen. Re-run the
gold set and record the calibration. `min_score` in particular is
reranker-scale dependent.

---

## Where things live

```
src/inflexis/
  contracts/    cross-plane contracts — change with care, everything binds here
  authz/        policy engine; the only minter of AuthorizedQuery
  governance/   AI registry (a gate), applicability matrices
  retrieval/    BM25, vector, RRF, rerank, corrective, pipeline, index
  models/       registry, gateway, offline provider
  tools/        registry, read-only catalogue
  audit/        append-only sink
  evaluation/   harness and metrics
  fixtures/     synthetic Acme ISD and Bravo ISD

governance/     district-facing data: matrices, policies, registries, gold sets
schemas/        JSON Schema for the wire contracts
tests/          security/, retrieval/, governance/
scripts/        CI hygiene and validation gates
```

---

## Phone-first development

This repository is built to be worked on without a local development
environment. Everything runs with no cloud credentials and no network: zero
runtime dependencies, offline model and embedding stand-ins, in-memory index,
synthetic fixtures.

If a change requires cloud access to test, it belongs behind an interface with
an offline implementation.
