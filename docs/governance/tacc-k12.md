# TACC / Texas AI in Education Task Force alignment

The Texas AI in Education Task Force direction, as summarised in the handoff,
emphasises four things:

1. Statewide AI leadership and strategy
2. Safe and effective K-12 AI guidance
3. Professional development
4. AI literacy in TEKS

> The white paper itself was **not retrievable** from the build environment.
> This alignment is written against the handoff's summary of its direction, not
> against the source. See [`source-registry.md`](source-registry.md).

---

## What this implies for positioning

The direction is not "districts should buy AI software." It is that districts
need governance, guidance, trained staff, and student AI literacy — with
technology as one component among several.

A vendor selling only a chatbot is answering a question the task force is not
asking.

The platform should therefore support:

```
Governance + Policy + Training + AI literacy
          + Implementation + Measurement + Technology
```

---

## Mapping

### 1. Leadership and strategy

| Need | Support | Status |
| --- | --- | --- |
| A district can state what AI it runs and who owns it | AI registry with named business and technical owners; gates production traffic | Implemented |
| A district can show its risk posture | Risk rubric, heightened-scrutiny register, overdue-review detection | Implemented |
| A district can produce evidence on request | Audit records, registry export, evaluation results, training records | Implemented |
| An AI Risk Officer has a defined role | `Role.AI_RISK_OFFICER`; escalation target in screening controls | Partial — role exists, no workflow |

### 2. Safe and effective K-12 guidance

| Need | Support | Status |
| --- | --- | --- |
| Clear prohibited uses | Screening controls with K-12-specific notes on social scoring and biometrics | Implemented |
| Human decision-making preserved | High-impact domains excluded from autonomy; oversight required for heightened scrutiny | Implemented |
| Students told they are talking to AI | Disclosure policy; approval blocked without a disclosure string for public-facing systems | Implemented |
| Answers that can be checked | Mandatory citations with page and section provenance | Implemented |
| Age-appropriate safeguards for student-facing use | — | **Not implemented.** The student role reaches public content only, which is a blunt instrument, not a safeguard. |

### 3. Professional development

| Need | Support | Status |
| --- | --- | --- |
| Training assigned and tracked | `TrainingRecord`; assignment, completion, certification, expiration | Implemented |
| Recurring training | `cadence_months` per course; expiry drives reassignment | Implemented |
| Role-appropriate content | Three courses: staff awareness, technical, governance | Implemented |
| Completion reporting | Completion targets, grace period, escalation path | Implemented |
| Course content itself | — | **Not provided.** Identifiers are placeholders for DIR-certified programs. |

### 4. AI literacy in TEKS

| Need | Support | Status |
| --- | --- | --- |
| Student-facing AI literacy | — | **Not implemented and out of scope for the platform.** |
| Modelling good practice | Every answer cites sources and refuses when evidence is thin — arguably the most useful literacy lesson a system can teach by example | Implicit |

---

## Honest positioning

Two of the four pillars are largely outside what software can deliver.

The platform contributes strongly to **governance** and **professional
development tracking**, contributes materially to **safe implementation
guidance**, and contributes almost nothing to **student AI literacy in TEKS**
beyond modelling grounded, citation-bearing, appropriately-refusing behaviour.

Inflexis should say this plainly. A district that buys the platform expecting
an AI literacy curriculum has been mis-sold, and will say so.

The credible claim is: *governance, security, and measurement infrastructure
that makes the district's own AI programme defensible* — with curriculum,
policy adoption, and professional development delivered as services alongside
it, not as features of the software.
