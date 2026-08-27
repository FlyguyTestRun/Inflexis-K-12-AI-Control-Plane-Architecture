# Source registry and verification status

Every external source this repository relies on, and **how thoroughly it was
actually verified**.

This document exists because a governance mapping whose provenance is unclear
is worse than no mapping — it invites reliance it has not earned.

---

## Verification conditions

Verification was attempted on 2026-08-26 from the build environment.

**`capitol.texas.gov` and `statutes.capitol.texas.gov` were blocked by the
network egress proxy.** Primary bill and statute text could not be read
directly. Verification proceeded against secondary legal and policy sources
(law firm analyses, legislative trackers, DIR publications).

This is a material limitation. It is recorded on every affected row rather
than glossed, and a test —
`test_unverified_rows_require_legal_review_or_are_not_asserted` — fails the
build if a `secondary_source_only` row claims a requirement definitively
applies to a district.

---

## Verification status values

| Status | Meaning |
| --- | --- |
| `primary_verified` | Primary text read directly |
| `secondary_source_only` | Derived from reputable secondary analysis; **must be re-verified before reliance** |
| `url_unverified` | URL recorded but not fetched |
| `well_established` | Long-standing law not in dispute (e.g. FERPA) |

---

## Texas legislation (89R)

| Bill | Subject | What secondary sources indicate | Status |
| --- | --- | --- | --- |
| **HB 149** | TRAIGA | Signed 2025-06-22, effective 2026-01-01. Substantially narrowed from the introduced version: most private-sector obligations removed, focus shifted to government use, prohibited purposes, and disclosure. AG-only enforcement, no private right of action. Creates a regulatory sandbox under a new AI Council within DIR. | `secondary_source_only` |
| **SB 1964** | Government AI governance | Signed 2025-06-20, effective 2025-09-01. Amends Gov't Code ch. 2054. Defines "artificial intelligence system", "consequential decision", "heightened scrutiny AI system". State agencies inventory AI and assess risk within IT strategic planning; **local governments** assess high-risk AI and share with DIR on request. DIR to develop a statewide AI code of ethics modelled on NIST AI RMF. | `secondary_source_only` |
| **HB 2818** | DIR AI division | Signed 2025-06-20, effective 2025-09-01. Creates an AI division within DIR to help state agencies modernise **legacy state government** computer systems using generative AI. | `secondary_source_only` |
| **HB 3512** | AI and cybersecurity training | Signed 2025-06-20, effective 2025-09-01. DIR certifies and periodically updates AI and cybersecurity training programs; requires certain state and local government employees **and school district employees** to complete them. | `secondary_source_only` |

### Codification correction

The handoff cites `BC.551.pdf` for the Texas Business & Commerce Code. TRAIGA's
**artificial-intelligence provisions are at Chapter 552** ("Artificial
Intelligence Protection"); the Act spans Chapters 551-554, with 551 covering
applicability and definitions.

Both are recorded here because a governance mapping that cites the wrong
chapter is worse than one that cites nothing.

### The critical open question

**Does an independent school district fall within SB 1964's definition of
"local government"?**

This single determination decides whether the AI inventory and risk assessment
provisions are a legal obligation for a Texas ISD or a recommended practice.
The bill's own definitions section must be read; it must not be assumed either
way.

The platform implements the control regardless, because an AI inventory is
independently justified by NIST AI RMF GOVERN-1 and by ordinary prudence. But
the *matrix* must not claim it is legally required until counsel says so.

---

## Primary source URLs (unfetched — blocked)

| Source | URL |
| --- | --- |
| HB 149 summary | `https://capitol.texas.gov/billlookup/BillSummary.aspx?Bill=HB149&LegSess=89R` |
| B&C Code ch. 552 (AI) | `https://statutes.capitol.texas.gov/Docs/BC/pdf/BC.552.pdf` |
| B&C Code ch. 551 | `https://statutes.capitol.texas.gov/Docs/BC/pdf/BC.551.pdf` |
| SB 1964 history | `https://capitol.texas.gov/billlookup/History.aspx?Bill=SB1964&LegSess=89R` |
| HB 2818 text | `https://capitol.texas.gov/tlodocs/89R/billtext/html/HB02818F.htm` |
| HB 3512 text | `https://capitol.texas.gov/tlodocs/89R/billtext/pdf/HB03512F.pdf` |
| TAC ch. 219 (adopted rules) | `https://www.sos.state.tx.us/texreg/archive/March132026/Adopted%20Rules/1.ADMINISTRATION.html` |

**Texas Administrative Code Chapter 219 was not verified at all.** The handoff
(§20) references it alongside SB 1964. Its existence, scope, and applicability
to districts are unconfirmed from this environment. No matrix row asserts a
Chapter 219 requirement; doing so on this evidence would be guessing.

---

## DIR resources

| Resource | URL | Status |
| --- | --- | --- |
| FY26-27 AI awareness training criteria | `https://dir.texas.gov/news/fiscal-year-26-27-criteria-ai-awareness-training-programs` | `url_unverified` |
| DIR implementation of 89th Legislature AI laws | `https://dir.texas.gov/news/ai-texas-dir-implementation-laws-89th-legislature` | `secondary_source_only` |
| DIR AI training and collaboration | `https://dir.texas.gov/ai-and-innovation/ai-training-and-collaboration` | `url_unverified` |
| DIR AI Acceptable Use Policy | `https://dir.texas.gov/sites/default/files/2026-04/AI%20Acceptable%20Use%20Policy.pdf` | `url_unverified` |

The DIR training criteria matter operationally: `governance/training/training-program.json`
uses **placeholder course identifiers**, which a district must replace with the
DIR-certified identifiers current at assignment time.

---

## Frameworks

| Framework | URL | Status |
| --- | --- | --- |
| NIST AI Risk Management Framework | `https://www.nist.gov/itl/ai-risk-management-framework` | `well_established` |
| NIST Generative AI Profile (AI 600-1) | `https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf` | `well_established` |
| OWASP Top 10 for LLM Applications | `https://owasp.org/www-project-top-10-for-large-language-model-applications/` | `well_established` |
| FERPA (34 CFR Part 99) | `https://www.ecfr.gov/current/title-34/subtitle-A/part-99` | `well_established` |

---

## K-12 direction

| Source | URL | Status |
| --- | --- | --- |
| TACC / UT Austin, Texas AI in Education Task Force white paper | `https://tacc.utexas.edu/media/filer_public/18/e5/18e507b4-4f78-4566-8261-d9e3bb1ae6dd/whitepaper-aiedu-061726.pdf` | `url_unverified` |

---

## Microsoft documentation

Referenced for the Azure reference deployment. Not verified from this
environment; treat version-specific details as needing confirmation before
implementation.

- Hybrid search overview · `https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview`
- Hybrid ranking (RRF) · `https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking`
- Search relevance · `https://learn.microsoft.com/en-us/azure/search/search-relevance-overview`
- Hybrid query how-to · `https://learn.microsoft.com/en-us/azure/search/hybrid-search-how-to-query`
- RAG design and evaluation · `https://learn.microsoft.com/en-gb/azure/architecture/ai-ml/guide/rag/rag-solution-design-and-evaluation-guide`
- Agentic retrieval overview · `https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-overview`

Agentic retrieval in particular should be checked against
[ADR-006](../architecture-decisions/ADR-006-preview-feature-isolation.md)
before any production dependency: confirm its current lifecycle stage rather
than assuming.

---

## Before a district relies on any of this

1. Re-verify every `secondary_source_only` row against primary statute text.
2. Obtain counsel's determination on SB 1964 applicability to ISDs.
3. Confirm whether TAC Chapter 219 exists in the referenced form and whether it
   reaches districts.
4. Replace placeholder training identifiers with current DIR-certified ones.
5. Confirm the lifecycle stage of every Azure capability in the deployment.
