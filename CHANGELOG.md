# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-08-26

First substantive commit. The repository previously contained a one-line
README and nothing else.

### Added — architecture

- Six-plane architecture: governance, identity and security, knowledge,
  adaptive retrieval, model and inference, tools and actions
- ADRs 001-006 covering the control plane, hybrid retrieval, authorization
  ordering, governance-first design, Azure-first vendor neutrality, and
  preview feature isolation
- Threat model, trust boundaries, architecture principles
- Project state, greenfield conflict report, decision log

### Added — contracts

- Identity, tenancy, roles, permissions, ABAC attributes
- Trust domains, data classification, authority hierarchy, document status
- Document, chunk, ACL, provenance
- Authorization: `RetrievalFilter`, `PolicyDecision`, and the unforgeable
  `AuthorizedQuery`
- Retrieval, model, tool, audit, evaluation, and governance contracts
- JSON Schema for document, chunk, AI system, tool, audit event, model, gold
  case, training record, and modernization measurement

### Added — implementation

- Deny-by-default policy engine; the only minter of `AuthorizedQuery`
- BM25 with a tokenizer that preserves policy codes such as `EIC(LOCAL)`
- Vector retrieval with content-hash-keyed embedding cache
- Reciprocal Rank Fusion
- Heuristic and provider rerankers behind one interface
- Corrective RAG: relevance, freshness, authority, and conflict gating with a
  bounded rewrite loop
- Model registry and gateway with trust-domain-aware routing and preview
  isolation
- Tool registry with per-invocation authorization and a read-only catalogue
- AI registry that gates production traffic
- Append-only audit sink; records carry identifiers and hashes, never content
- Evaluation harness measuring refusal correctness and treating leakage as a
  release blocker

### Added — governance data

- Texas applicability matrix with citations, applicability values, and
  verification status
- Prohibited-use screening controls, risk rubric, acceptable use and disclosure
  policy templates
- Synthetic Acme ISD AI inventory including a rejected social-scoring system
- Training program definition and model registry
- NIST AI RMF, NIST GenAI Profile, OWASP LLM Top 10, and TACC K-12 mappings,
  each stating its gaps

### Added — fixtures and tests

- Synthetic Acme ISD and Bravo ISD districts; no real data
- 91 tests covering role, campus, tenant, and trust-domain boundaries; tool
  authorization; direct and indirect prompt injection; retrieval quality;
  governance gates; and the full gold set
- 15-case Acme ISD gold set weighted toward refusal and leakage cases

### Added — tooling

- CI with separate security-gate and schema-validation jobs
- Repository hygiene check failing the build on secrets, real-data patterns,
  and silently weakened security controls

### Fixed during development

- Reranker treated authority and freshness as additive, giving irrelevant but
  authoritative documents a score floor that disabled the corrective gate.
  They now multiply coverage.
- The authority gate defaulted on platform-wide, rejecting campus and
  department documents that legitimately answer operational questions. It is
  now opt-in per use case.
- Relevance coverage counted every query term equally, so a question matching
  only filler words scored as a confident hit. Coverage is now weighted by term
  informativeness, with corpus statistics scoped per tenant.
- The corrective checker could return a provisional rewrite verdict that no
  caller could act on. `pipeline.answer()` now drives the loop to a terminal
  verdict.

### Corrected from the source handoff

- **HB 2818** was framed as a district measurement mandate. It creates an AI
  division within DIR for state legacy-system modernisation. Measurement is
  implemented as a product capability with
  `district_applicability: does_not_apply`.
- **TRAIGA citation** pointed at Business & Commerce Code chapter 551. The AI
  provisions are at chapter 552; the Act spans 551-554.

### Known limitations

See [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md). In brief: the offline
embedder is not semantic; thresholds are calibrated against a 15-document
synthetic corpus; conflict detection is structural, not semantic; governance
mappings rest on secondary sources because primary statute sites were
unreachable; and output validation, bias evaluation, incident response
workflow, and quota enforcement are specified but not implemented.
