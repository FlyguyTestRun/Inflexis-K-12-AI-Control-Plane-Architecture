# District onboarding

How a new district becomes a governed tenant. The goal is that district number
twelve costs a fraction of district number one — which only holds if
onboarding is configuration rather than engineering.

---

## Stage 1 — Governance before technology

Do this before provisioning anything. A district that starts with the index and
adds governance later never quite finishes.

- [ ] Name the **AI Risk Officer** or equivalent accountable role
- [ ] Adopt an AI acceptable use policy (start from
      `governance/policies/acceptable-use-policy.json`)
- [ ] Register the first use case — purpose, owners, affected population, data
      categories
- [ ] Run prohibited-use screening
- [ ] Classify risk using `governance/risk/risk-classification.json`
- [ ] **Legal review of the applicability matrix.** Counsel sets
      `district_applicability` for each row. The platform ships defaults of
      `requires_legal_review` precisely so this step cannot be skipped silently.
- [ ] Approve, with a review date. An approval without one counts as overdue.

## Stage 2 — Tenant configuration

- [ ] Allocate `tenant_id` and `district_id`
- [ ] Choose which trust domains this district provisions. Grants are
      intersected with this, so a domain the district never enables is
      unreachable regardless of role configuration.
- [ ] Map IdP groups → platform roles
- [ ] Configure ABAC attributes: campus and department identifiers
- [ ] Set authority overrides for levels 4-10 if the district's hierarchy
      differs. Levels 1-3 are fixed.
- [ ] Configure the disclosure string for public-facing systems

## Stage 3 — Identity

- [ ] Entra ID app registration
- [ ] Group-to-role mapping validated with real accounts
- [ ] Verify a token from another tenant cannot produce a principal here
- [ ] Decide whether anonymous public access is enabled

## Stage 4 — Content

The highest-risk stage. Everything downstream depends on getting classification
right here.

- [ ] Inventory source systems
- [ ] **Classify each source into a trust domain** — human decision, reviewed
- [ ] Assign authority levels
- [ ] Capture effective dates, expiration dates, versions, status
- [ ] Identify superseded documents and mark them, rather than deleting them
- [ ] Assign ACLs; human review for anything above `B_district_internal`
- [ ] Ingest, then **verify by sampling**: pick documents from each domain and
      confirm the intended roles can and cannot reach them

**Start narrow.** Board policy and public handbooks first. Personnel and
student records only after the assistant has been running on lower-risk
content long enough to trust the pipeline.

## Stage 5 — Gold set

- [ ] Collect 50-100 real questions from help desk, staff, and administration
- [ ] Write refusal cases for each sensitive domain
- [ ] Write **positive controls** for every refusal case
- [ ] Include this district's exact terminology — policy codes, form numbers
- [ ] Calibrate `min_score` per
      [`../evaluation/gold-set-spec.md`](../evaluation/gold-set-spec.md)
- [ ] Run; require zero security-gate failures

## Stage 6 — Training

- [ ] Assign AI awareness training to covered staff
- [ ] Assign technical training to IT staff
- [ ] Assign governance training to the AI Risk Officer
- [ ] Replace placeholder course identifiers with current DIR-certified ones
- [ ] Set reassignment cadence

## Stage 7 — Pilot

See [`pilot-plan.md`](pilot-plan.md).

## Stage 8 — Production

- [ ] Deployment status → `production` in the registry
- [ ] Alerting on `SECURITY` and `CRITICAL` audit events
- [ ] Review date set and calendared
- [ ] Baseline measurements captured for `ModernizationMeasurement`
- [ ] Feedback path live

---

## What must never be per-district code

If a district needs any of these changed in code rather than configuration, the
platform has a design defect and the fix belongs upstream:

- Trust domain semantics
- Authorization logic
- The retrieval pipeline
- Audit schema
- Governance contracts

Legitimately per-district: role mapping, authority overrides (4-10), enabled
trust domains, disclosure text, thresholds, gold set, source systems, model
selection.

---

## Realistic effort

| Stage | First district | Twelfth district |
| --- | --- | --- |
| Governance | 3-6 weeks (legal review dominates) | 1-2 weeks |
| Tenant config | 2-3 days | Hours |
| Identity | 1-2 weeks | 2-3 days |
| Content | 4-8 weeks | 2-4 weeks |
| Gold set | 2-3 weeks | 1-2 weeks |
| Training | 1 week | Days |
| Pilot | 6-8 weeks | 4 weeks |

Content and legal review dominate, and neither compresses much with
repetition — content because every district's document corpus is genuinely
different, legal review because it is genuinely per-district judgement. Any
onboarding estimate that assumes these shrink to nothing by the fifth district
is wrong.
