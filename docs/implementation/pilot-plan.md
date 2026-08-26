# Pilot plan

A pilot exists to answer one question: **would this district trust the system
enough to depend on it?** Everything else is secondary.

---

## Scope

**One use case: District Knowledge Assistant.** Board policy, administrative
regulations, public handbooks, and approved district procedures.

**Not in the pilot:** student records, personnel records, write actions,
agents, student-facing deployment.

The temptation is to include student data because that is where the impressive
demo lives. Resist it. The pilot's job is to establish that the pipeline is
trustworthy on low-risk content before it touches content where a mistake is
reportable.

---

## Participants

| Group | Count | Why |
| --- | --- | --- |
| Campus administrators | 3-5 | Ask policy questions constantly |
| Teachers | 10-15 | Highest volume, most varied phrasing |
| Central office staff | 3-5 | Ask procedural and purchasing questions |
| IT staff | 2-3 | Will actively try to break it, which is valuable |
| AI Risk Officer | 1 | Owns governance evidence |

Twenty to thirty people. Enough for real usage patterns, small enough that
every piece of feedback gets read.

---

## Timeline

**Weeks 1-2 — Preparation.** Ingest and verify content by sampling. Build the
gold set with district staff. Calibrate thresholds. Confirm zero security-gate
failures. Assign training.

**Weeks 3-4 — Closed pilot.** IT and administrators only. Daily review of every
question and answer. Fix retrieval gaps. Add every failure to the gold set.

**Weeks 5-8 — Open pilot.** Full participant group. Weekly review. Track
adoption and satisfaction. Capture baseline measurements for the processes the
assistant touches.

**Weeks 9-10 — Assessment.** Metrics against exit criteria. Governance evidence
package. Go/no-go.

---

## Exit criteria

**Must hold — no exceptions.**

- [ ] Zero security-gate failures across the full gold set
- [ ] Zero unauthorized retrievals in the audit log
- [ ] Zero cross-tenant events
- [ ] Every AI system registered, approved, with a review date
- [ ] Training completed by all participants
- [ ] Audit records can reconstruct any answer given

**Should hold — negotiable with documented rationale.**

- [ ] Refusal correctness > 95%
- [ ] Citation accuracy > 95%
- [ ] p95 latency < 3s
- [ ] User satisfaction > 4/5
- [ ] > 60% of participants using it weekly by week 8
- [ ] At least one process with a documented before/after measurement

---

## What to watch for

**Silent non-use.** The most common pilot failure is not a bad answer, it is
participants quietly stopping. Adoption tracking matters more than satisfaction
scores, because people who have stopped using something rate it politely.

**Over-refusal.** A system that refuses too much passes every security gate and
gets abandoned. Track refusal *rate* alongside refusal *correctness* — a rising
refusal rate on legitimate questions usually means the relevance floor is set
too high for this corpus.

**Terminology gaps.** Watch for questions that fail because the district's
vocabulary is not in the index. These are cheap to fix and disproportionately
damage trust when they persist.

**The first wrong answer.** It will happen. What matters is whether the system
was appropriately uncertain, whether the citation let the user catch it
quickly, and how fast it becomes a gold-set case. A confident wrong answer with
a plausible citation is the one to worry about.

---

## Governance evidence package

The pilot should end with a package the district can hand to its board or to
the state:

1. AI inventory export with approvals and risk classifications
2. Applicability matrix with counsel's determinations recorded
3. Evaluation report including security gates
4. Training completion records
5. Audit summary — volume, refusal rate, incidents
6. Before/after measurement for at least one process
7. Known limitations, stated plainly

Item 7 is the one that builds trust. A district that receives an
all-green report with no limitations will assume something was hidden — and
will be right to.

---

## Failure modes and responses

| Signal | Likely cause | Response |
| --- | --- | --- |
| Security gate fails | Authorization or ingestion defect | **Stop.** Root cause before any further rollout. |
| Refusal rate climbing | Threshold too high, or corpus gaps | Re-calibrate against the gold set; check terminology coverage |
| Adoption falling | Answers not useful, or too slow | Interview non-users specifically; do not infer from satisfaction scores |
| Wrong answers with citations | Ingestion metadata wrong — stale or misclassified content | Audit the source documents, not the model |
| Latency high | Reranking or retrieval cost | Profile before tuning; check candidate pool size first |
