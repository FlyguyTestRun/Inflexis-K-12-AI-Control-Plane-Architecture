# Project state

**Last updated:** 2026-08-26
**Phase:** 0 (architecture) complete; Phase 1 (governed hybrid RAG) reference
implementation in place
**Status:** pre-production. No district data, no deployed infrastructure.

---

## What this repository was before this pass

A single `README.md` containing one line of text.

There was no source code, no architecture documentation, no ADRs, no schemas,
no CI, and no tests. The repository was a name and nothing else.

This matters for reading the rest of the documentation: the handoff instructed
a careful reconciliation between an existing architecture and a proposed one.
There was no existing architecture to reconcile with, so
[`ARCHITECTURE_CONFLICT_REPORT.md`](ARCHITECTURE_CONFLICT_REPORT.md) records a
greenfield finding rather than a manufactured conflict list.

## What exists now

### Documentation

| Area | Location |
| --- | --- |
| Architecture overview | [`architecture.md`](architecture.md) |
| Architecture principles | [`architecture-principles.md`](architecture-principles.md) |
| Decision log | [`DECISION_LOG.md`](DECISION_LOG.md) |
| ADRs 001-006 | [`architecture-decisions/`](architecture-decisions/) |
| Trust boundaries | [`security/trust-boundaries.md`](security/trust-boundaries.md) |
| Threat model | [`security/threat-model.md`](security/threat-model.md) |
| Retrieval architecture | [`retrieval/retrieval-architecture.md`](retrieval/retrieval-architecture.md) |
| Strategy selection guide | [`retrieval/strategy-selection.md`](retrieval/strategy-selection.md) |
| Texas governance mapping | [`governance/texas-applicability.md`](governance/texas-applicability.md) |
| NIST AI RMF mapping | [`governance/nist-ai-rmf.md`](governance/nist-ai-rmf.md) |
| NIST GenAI profile mapping | [`governance/nist-genai-profile.md`](governance/nist-genai-profile.md) |
| OWASP LLM Top 10 mapping | [`governance/owasp-llm.md`](governance/owasp-llm.md) |
| TACC / K-12 alignment | [`governance/tacc-k12.md`](governance/tacc-k12.md) |
| Source registry + verification status | [`governance/source-registry.md`](governance/source-registry.md) |
| Evaluation framework | [`evaluation/evaluation-framework.md`](evaluation/evaluation-framework.md) |
| Gold set specification | [`evaluation/gold-set-spec.md`](evaluation/gold-set-spec.md) |
| Phase 1 implementation plan | [`implementation/phase-1-plan.md`](implementation/phase-1-plan.md) |
| District onboarding | [`implementation/district-onboarding.md`](implementation/district-onboarding.md) |
| Pilot plan | [`implementation/pilot-plan.md`](implementation/pilot-plan.md) |
| Azure GA vs preview | [`implementation/azure-ga-vs-preview.md`](implementation/azure-ga-vs-preview.md) |

### Code

| Plane | Package | State |
| --- | --- | --- |
| Cross-plane contracts | `src/inflexis/contracts/` | Complete for Phase 1 |
| 1 Governance | `src/inflexis/governance/` | Registry gate + applicability matrices |
| 2 Identity & security | `src/inflexis/authz/` | Deny-by-default policy engine |
| 3 Knowledge / data | `src/inflexis/retrieval/index.py` | In-memory reference index only |
| 4 Adaptive retrieval | `src/inflexis/retrieval/` | Hybrid + corrective implemented |
| 5 Model / inference | `src/inflexis/models/` | Registry, gateway, offline provider |
| 6 Tools / actions | `src/inflexis/tools/` | Registry + read-only catalogue |
| Audit | `src/inflexis/audit/` | Append-only in-memory sink |
| Evaluation | `src/inflexis/evaluation/` | Harness + metrics |
| Fixtures | `src/inflexis/fixtures/` | Acme ISD + Bravo ISD, fully synthetic |

### Tests

91 tests, all passing. `pytest -q`.

| Suite | Covers |
| --- | --- |
| `tests/security/test_authorization_boundaries.py` | Role, campus, tenant, and trust-domain boundaries |
| `tests/security/test_tool_authorization.py` | Tool denial, write blocking, descriptor invariants |
| `tests/security/test_prompt_injection.py` | Direct and indirect injection against authorization |
| `tests/retrieval/test_hybrid_retrieval.py` | BM25, RRF, reranking, freshness, corrective gate |
| `tests/retrieval/test_relevance_weighting.py` | Informativeness weighting, corrective loop |
| `tests/governance/test_governance.py` | Registry gate, review lifecycle, shipped data integrity |
| `tests/governance/test_evaluation.py` | Full gold set, leakage as a release blocker |

---

## What is deliberately NOT built

Naming these explicitly matters more than the list of what exists, because the
gap between "architected" and "implemented" is where a pilot goes wrong.

| Capability | Status | Why |
| --- | --- | --- |
| Real vector database | Not built | The in-memory index is a reference implementation. Production needs an Azure AI Search or PostgreSQL adapter. |
| Real embedding / LLM / reranker providers | Not built | Only offline test doubles exist. `HashingEmbeddingProvider` is not a semantic model. |
| Document ingestion pipeline | Not built | No OCR, PDF parsing, table extraction, or chunking strategy. Phase 2. |
| GraphRAG | Not built | Optional provider, Phase 2.5. See ADR-002. |
| Agentic RAG | Not built | Phase 3, and only over read-only tools. |
| Write tools | Declared, not implemented | Descriptors exist in `tools/catalog.py` so their risk posture is reviewable before anyone builds them. Phase 3.5. |
| Identity provider integration | Not built | `Principal` is constructed by tests. Entra ID integration is Phase 1 work. |
| Infrastructure as code | Not built | `infra/` holds a README describing intended shape only. |
| Persistent audit store | Not built | The sink is in-memory. Production needs append-only storage. |
| FinOps / quota enforcement | Partial | Cost is computed and audited; quotas and rate limits are not enforced. |

---

## Known limitations of what *is* built

1. **The offline embedding provider is not semantic.** It hashes tokens. It
   makes the pipeline testable without a model endpoint; it does not make the
   vector half of hybrid retrieval meaningful. Any claim about hybrid
   retrieval quality must be re-established against a real embedding model.
2. **Relevance thresholds are calibrated against a 15-document synthetic
   corpus.** `HeuristicReranker.default_min_score = 0.5` separates signal from
   noise in the fixture. It is a starting point for a district, not a tuned
   value. See [`evaluation/gold-set-spec.md`](evaluation/gold-set-spec.md).
3. **Conflict detection is structural, not semantic.** The corrective checker
   flags two active versions of the same document family at equal authority.
   It does not detect two documents that contradict each other in prose.
4. **The Texas applicability matrix is built from secondary sources.** Primary
   statute sites were unreachable from the build environment. Every affected
   row is marked `secondary_source_only` and requires verification. See
   [`governance/source-registry.md`](governance/source-registry.md).

---

## Next actions

In order, per [`implementation/phase-1-plan.md`](implementation/phase-1-plan.md):

1. Entra ID integration so `Principal` comes from a verified token.
2. Azure AI Search adapter implementing `Retriever` with filter pushdown.
3. Real embedding + reranking providers behind the existing interfaces.
4. Ingestion pipeline with provenance, starting with native-text PDFs.
5. Persistent append-only audit store.
6. Re-run the gold set against real providers and re-tune thresholds.
