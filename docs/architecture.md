# Architecture

The Inflexis K-12 AI Control Plane turns AI from a collection of applications a
district accumulates into a **governed capability the district operates**.

This document is the map. The reasoning behind each major choice lives in the
[ADRs](architecture-decisions/).

---

## 1. The shape of the system

```
                      DISTRICT GOVERNANCE
                              │
                              ▼
                 INFLEXIS AI CONTROL PLANE
                              │
   ┌──────────┬──────────┬────┴─────┬──────────┬──────────┐
   │ Identity │  Policy  │    AI    │  Model & │  Audit,  │
   │ Tenancy  │  engine  │ gateway  │   tool   │  obs,    │
   │ AuthZ    │          │          │ registry │  FinOps  │
   └──────────┴──────────┴────┬─────┴──────────┴──────────┘
                              ▼
                     INTENT / RISK ROUTER
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  STANDARD QUERY       COMPLEX RESEARCH          ACTION
        │                     │                     │
        ▼                     ▼                     ▼
   HYBRID RAG           AGENTIC RAG           TOOL GATEWAY
        │                     │                     │
        │            ┌────────┼────────┐            │
        │            ▼        ▼        ▼            │
        │         vector     web      SQL           │
        │            └────────┼────────┘            │
        │                     ▼                     │
        │                 reasoner                  │
        └──────────┬──────────┘                     │
                   ▼                                │
            BM25 + VECTOR                           │
                   ▼                                │
                  RRF                               │
                   ▼                                │
               RERANKER                             │
                   ▼                                │
         AUTHORIZATION / ACL  ◄─── re-check         │
                   ▼                                │
        AUTHORITY / FRESHNESS                       │
                   ▼                                │
          CORRECTIVE CHECK                          │
              ╱        ╲                            │
        sufficient   insufficient                   │
             │            │                         │
             │      rewrite / clarify               │
             │      escalate / refuse               │
             ▼                                      │
        MODEL GATEWAY  ◄──────────────────────────  │
                   ▼
          OUTPUT VALIDATION
                   ▼
          GROUNDED RESPONSE
              ╱        ╲
        CITATIONS      AUDIT
```

Note where authorization sits: **before** retrieval, with a second re-check
after it. Not after retrieval, and never delegated to the model. See
[ADR-003](architecture-decisions/ADR-003-authorization-before-retrieval.md).

---

## 2. The six planes

| Plane | Responsibility | Package |
| --- | --- | --- |
| 1 Governance | AI inventory, use-case registry, risk, approval, training, evidence | `governance/` |
| 2 Identity & security | Authentication, tenancy, RBAC, ABAC, document ACL, secrets | `authz/` |
| 3 Knowledge / data | Ingestion, parsing, metadata, chunking, indexes, provenance | `retrieval/index.py` |
| 4 Adaptive retrieval | Hybrid, corrective, multimodal, graph, agentic | `retrieval/` |
| 5 Model / inference | Model registry, gateway, routing, providers | `models/` |
| 6 Tools / actions | Tool registry, authorization, approval, execution | `tools/` |

Audit and evaluation cut across all six.

---

## 3. Tenancy

`tenant_id` is the hard isolation boundary. It is applied as a mandatory
predicate on every retrieval, every audit query, and every tool invocation.

No configuration, role, or policy widens a query across tenants. There is no
platform-admin bypass — a platform administrator administers the platform, not
every district's student records.

Tenants are co-located in one index in the realistic deployment (one search
service, many districts), so the isolation tests run that way too. Testing
isolation with one tenant per index proves only that separate indexes are
separate.

---

## 4. Identity and authorization

```
Identity → Tenant → Roles + Attributes → Entitlements → Policy
        → RetrievalFilter → Search
```

**Roles** answer "who is this person". **Permissions** answer "what has this
person been entitled to do". They are separate so a district can grant a narrow
capability without promoting someone into a broad role.

Role alone is never sufficient for a sensitive trust domain. A counselor role
without the `retrieve.student` permission does not reach student records — the
policy engine strips sensitive domains from a grant whose required permissions
are unmet.

**ABAC** narrows by campus and department as filter predicates, not post-hoc
checks. A north-campus teacher's filter excludes south-campus content at the
datastore, so that content is never read.

Districts map their own identity-provider groups onto platform roles through
tenant configuration. Authorization logic never consumes raw IdP group names,
because group naming differs per district and would otherwise leak into policy
code.

---

## 5. Trust domains

Content is partitioned. Not one unrestricted index.

| Domain | Contents |
| --- | --- |
| A Public | Board policy, public handbooks, public web content |
| B District internal | SOPs, procedures, internal documentation |
| C Personnel / HR | Compensation, grievances, personnel files |
| D Student confidential | Student records, discipline, accommodations |
| E Highly sensitive / SpEd | Special education case files |
| F Legal / privileged | Counsel communications, litigation |
| G Security / credentials | Security configuration, secrets, keys |

**F and G are unreachable by any general-purpose grant.** Access requires a
dedicated, separately approved AI use case with its own risk assessment. A test
asserts this holds for every synthetic principal including the superintendent.

Districts map their own classification labels onto these domains; the number
and ordering of domains is a platform invariant.

---

## 6. Authority, classification, and status are three different things

A common design error is to collapse these into one sensitivity scale. They
answer different questions:

- **Trust domain** — where content lives (index partitioning)
- **Data classification** — how carefully it must be handled
- **Authority level** — how much it should be believed

A public web page and a board policy may be equally non-sensitive while
carrying wildly different authority.

Default authority ranking (1 is highest):

| | Source |
| --- | --- |
| 1 | Texas law / official state source |
| 2 | Current board-approved district policy |
| 3 | District administrative regulation |
| 4 | Official district procedure |
| 5 | Current district handbook |
| 6 | Department documentation |
| 7 | Campus documentation |
| 8 | Approved internal knowledge |
| 9 | Approved external reference |
| 10 | Public web |

Levels 4-10 are district-configurable. Levels 1-3 are not, because state law
and board-approved policy outrank local documentation by definition.

**Authority weights ranking always. The authority *gate* is opt-in per use
case.** Applying a handbook-or-better gate platform-wide rejects campus and
department documents that legitimately answer operational questions — see
[D-008](DECISION_LOG.md#d-008--authority-gate-is-opt-in-per-use-case).

---

## 7. Retrieval

Default: BM25 + vector → RRF → rerank → re-filter → corrective check.

Full detail in
[`retrieval/retrieval-architecture.md`](retrieval/retrieval-architecture.md);
strategy choice in
[`retrieval/strategy-selection.md`](retrieval/strategy-selection.md).

The corrective layer treats **"we do not have good enough evidence" as a
correct outcome**, not an error to paper over. It never invents evidence and
never lowers its own bar to produce an answer.

---

## 8. Models

Every inference goes through the model gateway. Two properties matter most:

- **Model approval constrains where content may be sent**, independently of
  what the user may read. A counselor entitled to read student records cannot
  cause that content to reach a model not approved for it.
- **Preview models are excluded from default routing.** Reaching one requires
  asking explicitly. See
  [ADR-006](architecture-decisions/ADR-006-preview-feature-isolation.md).

The registry refuses to construct a descriptor combining
`vendor_may_train_on_data` with any non-public approved domain.

---

## 9. Tools and actions

Every tool declares its full security posture before it can be registered:
risk level, read-only status, required roles and permissions, tenant scope,
data domains, credential scope, human-approval requirement, audit requirement,
reversibility, and rollback support.

A tool that cannot fill this in is not ready to be exposed to an agent.
Contract invariants refuse tools that declare no required roles, disable audit,
or combine high-risk writes with no human approval.

**Phase 3 begins read-only.** Write tools are declared in the catalogue without
implementations so their risk posture is reviewable before anyone builds them.

An agent planner is shown only the tools the *caller* may actually invoke.
Advertising unusable tools invites the model to plan around capabilities it
will then be denied.

---

## 10. High-impact decisions

The platform does not make autonomous decisions about:

student discipline · special education eligibility or placement · admissions ·
course placement · hiring or employment · student record mutation

These require human review. A heightened-scrutiny AI system cannot even be
*registered* without a documented human-oversight mechanism — the contract
refuses to construct the record.

---

## 11. Audit

Every authorization decision, retrieval, refusal, generation, tool invocation,
tool denial, and governance change emits an audit record.

**Audit records carry identifiers, hashes, and decisions — never retrieved
document text.** Copying confidential content into the audit log creates a
second, usually less well protected, copy of the data.

A filter violation — the backend returning content the in-process re-check
rejects — is audited at `SECURITY` severity as an incident, not logged as a
warning.

---

## 12. Evaluation

Retrieval, generation, security, system, governance, and business metrics.
Detail in
[`evaluation/evaluation-framework.md`](evaluation/evaluation-framework.md).

The distinguishing properties: **refusal correctness is measured** (a case
whose right answer is "I cannot answer that" fails if the system answers,
however fluently), and **leakage is a release blocker** rather than a score to
average into an aggregate.

---

## 13. What a production deployment adds

The repository ships reference implementations that make the architecture
testable without cloud access. A district deployment replaces:

| Reference | Production |
| --- | --- |
| `InMemoryIndex` | Azure AI Search or PostgreSQL with filter pushdown |
| `HashingEmbeddingProvider` | A real embedding model |
| `HeuristicReranker` | A cross-encoder reranking service |
| `EchoModelProvider` | Azure OpenAI / Foundry |
| `InMemoryAuditSink` | Append-only audit storage |
| Test-constructed `Principal` | Entra ID token validation |

See [`PROJECT_STATE.md`](PROJECT_STATE.md) for what is built and what is not.
