# Texas AI governance — applicability and controls

**This document is an engineering artifact. It is not legal advice, and
nothing in this repository asserts that deploying the platform makes a district
compliant with any statute or rule.**

The machine-readable matrix is
[`../../governance/texas/applicability-matrix.json`](../../governance/texas/applicability-matrix.json).
Verification provenance is in [`source-registry.md`](source-registry.md).

---

## How to read the matrix

Each row carries:

| Field | Purpose |
| --- | --- |
| `requirement_id` | Stable handle |
| `source` / `statute_or_rule` / `citation_url` | What it is and where to read it |
| `actor` | **Who the requirement is addressed to** — often not the district |
| `district_applicability` | Counsel's determination; defaults to `requires_legal_review` |
| `required_control` | The engineering control that would satisfy it |
| `implemented_by` | Where that control lives in this repository |
| `evidence` | What the district can produce in a review |
| `verification_status` | How well the source itself was verified |

The `actor` field does a lot of quiet work. Several 89R AI bills address
**DIR**, not districts. A requirement imposed on a state agency is not a
district obligation, however AI-related it sounds.

---

## Applicability values

| Value | Meaning |
| --- | --- |
| `applies` | Established as applicable |
| `does_not_apply` | Established as not applicable to districts |
| `conditional` | Applies to some employees, uses, or circumstances |
| `requires_legal_review` | **Default.** Not determinable from statute text alone |
| `recommended_practice` | Not a legal requirement; adopt anyway |

`requires_legal_review` is the default and it is load-bearing. A district that
believes the software resolved applicability will skip the review only its
counsel can perform.

---

## Summary

| ID | Source | Actor | District applicability | Control status |
| --- | --- | --- | --- | --- |
| `TX-HB149-PROHIBITED-USE` | HB 149 (TRAIGA) | developer/deployer | requires legal review | Implemented |
| `TX-HB149-GOV-DISCLOSURE` | HB 149 (TRAIGA) | governmental agency | requires legal review | Implemented |
| `TX-SB1964-AI-INVENTORY` | SB 1964 | state agency; local government | requires legal review | Implemented |
| `TX-SB1964-HEIGHTENED-SCRUTINY` | SB 1964 | state agency; local government | requires legal review | Implemented |
| `TX-HB3512-AI-TRAINING` | HB 3512 | DIR; state, local, **and school district** employees | conditional | Implemented |
| `TX-HB2818-MODERNIZATION` | HB 2818 | **DIR** | does not apply | Implemented as product capability |
| `TX-DIR-AUP` | DIR | state agencies | recommended practice | Implemented |
| `TX-TEC-STUDENT-RECORDS` | FERPA / TEC | school district | **applies** | Implemented |

---

## The two rows that matter most

### FERPA / student records — the one that definitely applies

`TX-TEC-STUDENT-RECORDS` is the only row marked `applies`, and it predates
every 89R AI bill. It is also the obligation most likely to be tested in
practice, and the one the platform's architecture is most directly shaped by:
trust-domain separation, authorization before retrieval, entitlements beyond
role membership, and full retrieval audit all exist primarily because of it.

If the AI legislation were repealed tomorrow, this row would still drive the
architecture.

### HB 3512 — the clearest AI-specific hook to districts

Secondary sources state the bill names **school district employees** explicitly.
That makes it the AI-specific requirement with the most direct district
connection.

Marked `conditional` rather than `applies` because *which* employees are
covered and on what cadence must be read from primary text and from the DIR
certification criteria. The control — assignment, completion, certification,
expiration, and recurring reassignment tracking — is implemented either way.

---

## The critical open question

**Is a Texas ISD a "local government" under SB 1964?**

This determination decides whether AI inventory and risk assessment are legal
obligations or recommended practice for a district. It must be read from the
bill's definitions, not assumed.

The platform implements the control regardless. An AI inventory is
independently justified by NIST AI RMF GOVERN-1, and a district that cannot
answer "what AI is running here" has a problem whether or not a statute says
so.

---

## Prohibited-use screening

[`../../governance/texas/policy-controls.json`](../../governance/texas/policy-controls.json)
turns reported TRAIGA prohibited-use topics into **screening questions asked at
use-case registration**, before anything is built.

These are screening prompts for a human reviewer, not legal determinations. A
blocked registration escalates to the AI Risk Officer and counsel; it is not
silently refused.

| Control | Category | On match |
| --- | --- | --- |
| `PU-MANIPULATION` | Harmful behavioural manipulation | Block |
| `PU-INCITEMENT` | Incitement | Block |
| `PU-SOCIAL-SCORING` | Governmental social scoring | Block |
| `PU-BIOMETRIC` | Biometric identification without consent | Block |
| `PU-CONSTITUTIONAL` | Constitutional rights | Escalate |
| `PU-DISCRIMINATION` | Unlawful discrimination | Escalate |
| `PU-CSAM-SEXUAL-EXPLOITATION` | Covered sexual exploitation / CSAM | Block |
| `DISC-AI-INTERACTION` | AI interaction disclosure | Require disclosure |

**Two of these deserve specific attention in a K-12 setting**, because the
district version does not look like the statutory description:

- **`PU-SOCIAL-SCORING`.** Composite "student risk scores" assembled from
  attendance, discipline, and behaviour data to allocate services or scrutiny
  are the district-flavoured form of social scoring. They are usually proposed
  with entirely good intentions. The synthetic Acme ISD inventory includes one,
  rejected, retained as evidence the control fired.
- **`PU-BIOMETRIC`.** Campus safety and visitor-management vendors frequently
  ship facial recognition on by default. Screening applies to *procured*
  systems, not only to systems the district builds.

---

## What the platform will not do

- Assert that a district is compliant.
- Assert that a requirement applies without counsel's determination.
- Hard-code a legal conclusion in application logic.
- Silently update applicability when law changes — changes are versioned in the
  matrix and surfaced for review.
