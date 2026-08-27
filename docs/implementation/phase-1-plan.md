# Phase 1 implementation plan — governed hybrid RAG

**Goal:** one district, one use case (District Knowledge Assistant), running on
real infrastructure with every architectural guarantee intact.

**Non-goal:** breadth. A second use case before the first is production-solid
multiplies unfinished work.

---

## Where Phase 1 starts

Already built and tested (91 tests):

- Contracts for identity, documents, authorization, retrieval, models, tools,
  audit, evaluation, governance
- Deny-by-default policy engine with unforgeable `AuthorizedQuery`
- Hybrid retrieval: BM25 + vector → RRF → rerank → re-filter → corrective gate
- Governance registry as a production gate
- Model registry and gateway with trust-domain-aware routing
- Tool registry with read-only catalogue
- Evaluation harness and a 15-case gold set
- Synthetic two-district fixture and full security test suite

What is missing is everything that touches the outside world.

---

## Workstreams

### W1 — Identity (blocking everything else)

Today `Principal` is constructed by tests. Nothing validates a token.

- [ ] Entra ID OIDC integration; validate signature, issuer, audience, expiry
- [ ] Map IdP group claims → platform roles via **tenant configuration**, never
      by consuming raw group names in policy code
- [ ] Derive ABAC attributes (campus, department) from claims or a directory
      lookup
- [ ] Resolve tenant from the token, never from a request parameter
- [ ] Service principals for background jobs, with their own scoped roles
- [ ] Anonymous public access path constrained to the public trust domain

**Done when:** a real Entra token produces a `Principal`, and a token from
district A cannot produce a principal in district B.

### W2 — Retrieval backend

- [ ] Azure AI Search adapter implementing `Retriever`
- [ ] **Filter pushdown** — translate `RetrievalFilter` into `$filter`
      server-side. A backend that cannot do this is unusable under ADR-003.
- [ ] Index schema from `schemas/chunk.schema.json`
- [ ] Tenant partitioning strategy (index-per-tenant vs. filtered shared index)
      with an explicit decision recorded
- [ ] Confirm native hybrid + RRF behaviour matches our contract, or keep
      fusion in-process
- [ ] Adapter conformance tests reusing the existing security suite

**Watch for:** the adapter that fetches then filters. It passes the in-process
re-check while having already read unauthorized rows out of the datastore.

### W3 — Model providers

- [ ] Azure OpenAI `ModelProvider` and `EmbeddingProvider`
- [ ] Reranking provider behind `RerankerProvider`
- [ ] Key Vault-backed credentials, referenced by identity not value
- [ ] Populate the model registry with real costs, context sizes, lifecycle
- [ ] Confirm and record vendor training terms per model
- [ ] Retry, timeout, and circuit-breaking with graceful degradation to
      `HeuristicReranker` when reranking is unavailable

### W4 — Ingestion

- [ ] Native-text PDF and DOCX extraction (defer OCR to Phase 2)
- [ ] Chunking that preserves section and page provenance
- [ ] Metadata capture: authority, effective/expiration dates, version, status
- [ ] **ACL assignment at ingest** — the highest-risk step in the whole system
- [ ] Content hashing and duplicate detection
- [ ] Re-ingestion that supersedes rather than duplicates
- [ ] Ingestion audit events

**The critical control:** a document ingested with the wrong trust domain
defeats every downstream control. Ingestion needs human review of ACL
assignment for anything above `B_district_internal`, at least initially.

### W5 — Audit persistence

- [ ] Append-only audit store (immutable table or Azure Monitor)
- [ ] Retention policy aligned with district records retention
- [ ] Query interface for the AI Risk Officer
- [ ] Alerting on `SECURITY` and `CRITICAL` severity
- [ ] Verify records still exclude document content end to end

### W6 — API and application surface

- [ ] HTTP API enforcing governance admission (`assert_may_serve`) per request
- [ ] Disclosure presented for public-facing systems
- [ ] Citations rendered so a user can open the source
- [ ] Refusals that explain *why* without leaking what exists
- [ ] Feedback capture — the cheapest source of real evaluation signal

**Refusal wording matters.** "You are not authorized to see the HR grievance
file" confirms the file exists. "I could not find district information I can
share with you about that" does not.

### W7 — Evaluation against reality

- [ ] Build a real district gold set (50-100 cases) with district staff
- [ ] Re-run with real providers; **re-tune `min_score`**
- [ ] Re-establish hybrid retrieval quality claims against a real embedding
      model — the offline hashing embedder proves plumbing, not semantics
- [ ] Wire gold set into CI as a release gate

### W8 — Infrastructure

- [ ] Container image and Container Apps or AKS deployment
- [ ] Terraform or Bicep for search, storage, Key Vault, monitoring
- [ ] Network controls: private endpoints, no public datastore exposure
- [ ] Managed identity throughout; no connection strings
- [ ] Environments: dev, staging with synthetic data, production

---

## Sequencing

```
W1 identity ──┬─► W2 retrieval backend ──┬─► W7 evaluation
              ├─► W3 model providers ────┤
              └─► W5 audit persistence ──┘
                        │
              W4 ingestion ──► W6 API ──► W8 infrastructure
```

W1 blocks everything: without real identity there is nothing to authorize.
W4 can proceed in parallel but cannot be validated until W2 exists.

---

## Definition of done

- [ ] A real user authenticates via Entra and receives an answer with citations
- [ ] All 91 existing tests pass unchanged against real adapters
- [ ] The district gold set passes with **zero** security-gate failures
- [ ] An unauthorized user's query returns a refusal that does not confirm
      existence
- [ ] Audit records reconstruct any answer: who, what, which evidence, which
      model, what cost
- [ ] The AI system is registered, approved, and gated on registration
- [ ] No secrets in the repository; no real data in non-production
- [ ] A district administrator can produce an AI inventory export unaided

---

## Explicitly deferred

| Deferred to | What |
| --- | --- |
| Phase 1.5 | Query rewriting, richer conflict detection, escalation workflow |
| Phase 2 | OCR, scanned PDFs, tables, charts, images |
| Phase 2.5 | GraphRAG |
| Phase 3 | Agentic retrieval over read-only tools |
| Phase 3.5 | Write tools, approval workflow, rollback |
| Ongoing | Bias evaluation harness, incident response workflow, quota enforcement, output validation |

The last row is the uncomfortable one: those four are known gaps in a
governance product, documented in
[`../governance/nist-ai-rmf.md`](../governance/nist-ai-rmf.md) and
[`owasp-llm.md`](../governance/owasp-llm.md). They should not stay open past
the first production district.
