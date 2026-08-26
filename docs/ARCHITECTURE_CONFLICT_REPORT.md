# Architecture conflict report

**Date:** 2026-08-26
**Author:** Implementation pass against the CTO handoff of the same date
**Verdict:** No architectural conflicts. The repository was greenfield.

---

## 1. Finding

The handoff instructed a careful reconciliation between the existing repository
architecture and the proposed control-plane architecture, with explicit
instructions not to replace working architecture merely because the handoff
proposes a different structure.

**There was no existing architecture.** The repository at commit `8efad13`
contained exactly one file:

```
README.md   (45 bytes, one heading line)
```

No source code. No `CLAUDE.md` or `AGENTS.md`. No ADRs. No schemas. No
identity, RBAC, or MAOP/orchestration code. No infrastructure, deployment
configuration, CI/CD, or tests. No database definitions.

Consequently there is nothing to migrate, nothing to preserve, and no conflict
to resolve. Reporting a conflict list here would be fabricating one.

## 2. Consequences for the handoff

Three parts of the handoff assume prior work that does not exist:

| Handoff item | Assumption | Actual |
| --- | --- | --- |
| §1 "Read CLAUDE.md, AGENTS.md, existing ADRs, existing skills" | These exist | None existed. `CLAUDE.md` is created by this pass. |
| §34 ADR-001 "MAOP becomes the control/orchestration layer" | MAOP exists as a component to be repurposed | No MAOP code exists. ADR-001 defines the control plane from scratch and records MAOP as an external concept the handoff refers to, not as inherited code. |
| §33 "Do not create duplicate structures if the repository already contains equivalent functionality" | Possible duplication | No duplication possible. |

None of these blocked the work. They are recorded so that a reader of ADR-001
is not left looking for a MAOP module that was never here.

## 3. Conflicts *within* the handoff, and how they were resolved

There were no repository-vs-handoff conflicts. There were four internal
tensions in the handoff itself that had to be resolved to implement it
coherently. Each is recorded in [`DECISION_LOG.md`](DECISION_LOG.md) with fuller
reasoning.

### 3.1 HB 2818 framed as a district measurement mandate

**Handoff §21** presents HB 2818 as requiring districts to track baseline
versus AI-assisted time, cost, and resources, and says "this should become a
core product metric."

**Finding.** On the available evidence, HB 2818 creates an artificial
intelligence division *within the Texas Department of Information Resources*,
tasked with helping state agencies modernise legacy state computer systems. It
is an agency-structure bill. It does not, on its face, impose a
modernisation-measurement duty on independent school districts.

**Resolution.** Measurement is implemented in full as a **product capability**
(`ModernizationMeasurement`, `schemas/modernization-measurement.schema.json`)
because a district genuinely needs to demonstrate that AI improved a process.
It is recorded in the Texas matrix with
`district_applicability: does_not_apply` and an explanatory note. Presenting a
product feature as a legal obligation is precisely the overclaiming the
handoff's own §18 forbids.

### 3.2 TRAIGA citation points at the wrong chapter

**Handoff §40** cites `https://statutes.capitol.texas.gov/Docs/BC/pdf/BC.551.pdf`
for the Texas Business & Commerce Code.

**Finding.** TRAIGA's artificial-intelligence provisions appear at **Chapter
552** ("Artificial Intelligence Protection"); the Act spans Chapters 551-554,
with 551 covering applicability and definitions.

**Resolution.** The matrix cites Chapter 552 for the substantive AI provisions
and notes the wider 551-554 span. Recorded because a governance mapping that
cites the wrong chapter is worse than one that cites nothing.

### 3.3 Blanket authority threshold would break ordinary questions

**Handoff §8 and §15** describe an authority check as part of the standard
corrective-RAG pipeline, with a default authority hierarchy in which district
handbooks rank fifth and campus documents seventh.

**Finding.** Applying an authority *gate* at the platform level with a
handbook-or-better threshold rejects campus documents, department
documentation, and student records — which are the authoritative sources for
most operational questions. Implemented literally, the assistant refuses to
answer "what time does first period start."

**Resolution.** Authority always influences *ranking*. The authority *gate* is
opt-in per use case, enabled by the router for policy and compliance
questions. This is implemented and tested both ways
(`tests/retrieval/test_hybrid_retrieval.py::TestAuthorityGate`).

### 3.4 "Verify sources before treating them as requirements" vs. a blocked network

**Handoff §40** instructs verification of legislation and API status before
treating any source as an active production requirement.

**Finding.** `capitol.texas.gov` and `statutes.capitol.texas.gov` are blocked
by this environment's network egress proxy. Primary statute text could not be
read.

**Resolution.** Verification was performed against secondary legal and policy
sources, and **every affected row records
`verification_status: secondary_source_only`**. A test
(`test_unverified_rows_require_legal_review_or_are_not_asserted`) enforces that
no such row asserts `applies`. See
[`governance/source-registry.md`](governance/source-registry.md) for the full
verification ledger.

## 4. Risk assessment

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Governance mappings rest on secondary sources | **High** | Every row carries verification status and a legal-review flag; a test prevents unverified rows from asserting applicability. Must be re-verified against primary text before any district relies on it. |
| Whether an ISD is a "local government" under SB 1964 is unresolved | **High** | Flagged as the critical open question in the matrix. The control (AI inventory) is implemented regardless, because NIST AI RMF GOVERN-1 justifies it independently. |
| Retrieval quality claims rest on an offline hashing embedder | Medium | Documented in `PROJECT_STATE.md`. Claims must be re-established against real providers before a pilot. |
| Thresholds tuned on a 15-document synthetic corpus | Medium | Documented; gold-set spec requires re-tuning per district. |
| No migration risk | None | Greenfield. |

## 5. Recommendation

Proceed with the architecture as specified, with the four resolutions above
carried forward. Before any district pilot:

1. Re-verify every `secondary_source_only` row against primary statute text.
2. Obtain district counsel's determination on SB 1964 applicability to ISDs.
3. Re-run the gold set against real embedding, reranking, and generation
   providers, and re-tune the relevance floor.
