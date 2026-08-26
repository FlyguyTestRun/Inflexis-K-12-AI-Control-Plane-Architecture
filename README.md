# Inflexis K-12 AI Control Plane

A governed AI control plane for Texas K-12 school districts.

> **AI should become a governed capability of the district — not an
> uncontrolled collection of AI applications.**

**Status:** pre-production. Architecture phase complete; a working reference
implementation of governed hybrid retrieval is in place. No district data, no
deployed infrastructure. See [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
for exactly what is and is not built.

---

## The problem

A district that buys an AI chatbot gets an AI *application*: one assistant, one
corpus, one permission model baked in by whoever built it. When the second use
case arrives, the district builds a second application with its own corpus, its
own permissions, and its own audit story.

Within a year the district cannot answer the first question in any AI
governance review: **what AI is running here, who approved it, and what data
does it touch?**

## The approach

Build the control plane first. Identity, tenancy, authorization, policy, model
gateway, tool registry, audit, and evaluation are platform concerns that every
AI use case inherits. A use case is a registered entry in that control plane,
not a separate stack.

Adding a second use case means adding a registry entry and a configuration.

---

## What makes this different

**Authorization happens before retrieval, and it is structurally enforced.**
Retrievers accept an `AuthorizedQuery`, which cannot be constructed by calling
code — only a policy decision point can mint one. A developer *cannot* call a
retriever without proof that authorization occurred. No unauthorized content
enters model context, ever.

**Prompt injection cannot escalate privilege**, because authorization is
computed from the authenticated principal and never reads text. There is no
code path from a query, a document, or a model response to an entitlement.

**Hybrid retrieval by default.** District knowledge is saturated with exact
terminology — `EIC(LOCAL)`, `TEC §25.085`, `DAEP`, `504`, `HB 149`. BM25 finds
those; vector search finds paraphrase; RRF fuses them without pretending their
scores are comparable.

**Refusal is a correct outcome.** The corrective layer treats "we do not have
good enough evidence" as success. It never invents evidence and never lowers
its own bar to produce an answer.

**Governance is on the request path.** An AI system absent from the inventory
cannot serve traffic, so the inventory cannot drift from reality.

**The repository does not claim legal compliance.** Governance mappings carry
citations, applicability values, verification status, and a legal-review flag.
A test fails the build if a row built from secondary sources asserts that a
requirement definitively applies.

---

## Quick start

```bash
pip install -e ".[dev]"
pytest -q                 # 91 tests
ruff check src tests
python scripts/check_repository_hygiene.py
```

Run the synthetic district end to end:

```python
from inflexis.authz import PolicyEngine
from inflexis.fixtures import ACME, build_two_tenant_index, principals
from inflexis.retrieval import (
    BM25Retriever, VectorRetriever, HeuristicReranker, HybridRetrievalPipeline,
)

index = build_two_tenant_index()
engine = PolicyEngine(ACME)
pipeline = HybridRetrievalPipeline(
    retrievers=[BM25Retriever(index), VectorRetriever(index)],
    reranker=HeuristicReranker(),
)

people = principals()

# A teacher asks a policy question -> grounded answer with citations
query = engine.authorize_retrieval(people["teacher"], "What does EIC(LOCAL) say about class ranking?")
result = pipeline.answer(query)
print(result.verdict.action.value, result.citations)

# The same teacher asks for HR records -> refusal, no evidence returned
query = engine.authorize_retrieval(people["teacher"], "Show me the employee grievance case notes")
result = pipeline.answer(query)
print(result.verdict.action.value, result.evidence)
```

---

## Architecture

Six planes: governance, identity and security, knowledge, adaptive retrieval,
model and inference, tools and actions. Audit and evaluation cut across all
six.

```
AuthorizedQuery ──► BM25 + vector ──► RRF ──► rerank ──► re-filter
                                                             │
                                                             ▼
                                                    corrective check
                                                      ╱          ╲
                                                 generate      refuse /
                                                               clarify /
                                                               escalate
```

Start with [`docs/architecture.md`](docs/architecture.md).

---

## Documentation

| | |
| --- | --- |
| **Start here** | [`docs/architecture.md`](docs/architecture.md) · [`docs/architecture-principles.md`](docs/architecture-principles.md) |
| **What's built** | [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) |
| **Why it's built this way** | [`docs/architecture-decisions/`](docs/architecture-decisions/) · [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) |
| **Greenfield finding** | [`docs/ARCHITECTURE_CONFLICT_REPORT.md`](docs/ARCHITECTURE_CONFLICT_REPORT.md) |
| **Security** | [`docs/security/threat-model.md`](docs/security/threat-model.md) · [`docs/security/trust-boundaries.md`](docs/security/trust-boundaries.md) |
| **Retrieval** | [`docs/retrieval/retrieval-architecture.md`](docs/retrieval/retrieval-architecture.md) · [`docs/retrieval/strategy-selection.md`](docs/retrieval/strategy-selection.md) |
| **Governance** | [`docs/governance/texas-applicability.md`](docs/governance/texas-applicability.md) · [`nist-ai-rmf`](docs/governance/nist-ai-rmf.md) · [`owasp-llm`](docs/governance/owasp-llm.md) · [`tacc-k12`](docs/governance/tacc-k12.md) · [`source-registry`](docs/governance/source-registry.md) |
| **Evaluation** | [`docs/evaluation/evaluation-framework.md`](docs/evaluation/evaluation-framework.md) · [`gold-set-spec`](docs/evaluation/gold-set-spec.md) |
| **Delivery** | [`phase-1-plan`](docs/implementation/phase-1-plan.md) · [`district-onboarding`](docs/implementation/district-onboarding.md) · [`pilot-plan`](docs/implementation/pilot-plan.md) |

---

## Architecture decisions

| ADR | Decision |
| --- | --- |
| [001](docs/architecture-decisions/ADR-001-governed-control-plane.md) | A governed control plane, not an AI application |
| [002](docs/architecture-decisions/ADR-002-hybrid-rag.md) | Hybrid BM25 + vector with RRF is the default |
| [003](docs/architecture-decisions/ADR-003-authorization-before-retrieval.md) | Authorization happens before retrieval |
| [004](docs/architecture-decisions/ADR-004-governance-first.md) | Governance is a first-class architectural component |
| [005](docs/architecture-decisions/ADR-005-azure-first-vendor-neutral.md) | Azure is the reference deployment; interfaces stay portable |
| [006](docs/architecture-decisions/ADR-006-preview-feature-isolation.md) | Preview features must not become silent production dependencies |

---

## Honest limitations

- The offline embedding provider **hashes tokens**; it is not a semantic model.
  Hybrid retrieval quality claims must be re-established against a real
  embedding model.
- Relevance thresholds are calibrated against a **15-document synthetic
  corpus** and must be re-tuned per district.
- Conflict detection is **structural, not semantic** — it catches version
  conflicts, not prose contradictions.
- Texas governance mappings are built from **secondary sources**; primary
  statute sites were unreachable from the build environment. Every affected row
  says so.
- Bias evaluation, incident response workflow, output validation, and quota
  enforcement are **specified but not implemented**.

Full detail: [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md).

---

## No real data, no secrets

Every fixture is synthetic. Acme ISD and Bravo ISD are invented, as is every
document, person, campus, and policy code in them. CI fails the build on
credentials, real-identifier patterns, or silently weakened security controls.

See [`SECURITY.md`](SECURITY.md).
