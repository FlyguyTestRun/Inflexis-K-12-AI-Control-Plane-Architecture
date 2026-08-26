# Evaluation framework

"The chatbot sounds good" is not a measurement. Six metric families, with an
explicit statement of which are **scores to improve** and which are **gates
that block release**.

---

## The distinction that matters

| Family | Type |
| --- | --- |
| Retrieval | Score |
| Generation | Score |
| **Security** | **Gate** |
| System | Score, with SLO thresholds |
| Governance | Gate for some, score for others |
| Business | Score |

Security metrics are not averaged into an aggregate quality number. A single
cross-tenant leak is not offset by a high recall score, and a system that
computes a blended figure will eventually ship one.

`SecurityMetrics.is_clean` is a boolean, and `EvaluationReport.release_blocked`
derives from it directly.

---

## 1. Retrieval metrics

| Metric | Question |
| --- | --- |
| Recall@K | Did we retrieve the documents that should have been retrieved? |
| Precision@K | How much of what we retrieved was relevant? |
| MRR | How high did the first correct result rank? |
| nDCG | How good is the ranking overall? |
| Hit rate | What fraction of queries retrieved anything correct? |
| **Authority hit rate** | Did we retrieve a source of sufficient authority? |
| **Freshness hit rate** | Was everything we retrieved current? |

The last two are the K-12-specific ones. A retrieval that finds the *right
topic* in a *superseded* regulation scores well on recall and is wrong in the
way that matters.

## 2. Generation metrics

| Metric | Question |
| --- | --- |
| Groundedness | Is every claim supported by retrieved evidence? |
| Correctness | Is the answer right? |
| Completeness | Does it answer the whole question? |
| Citation accuracy | Do citations point at sources that support the claim? |
| **Refusal correctness** | Did it refuse when it should have, and only then? |
| Confabulation rate | How often does it assert unsupported content? |

**Refusal correctness is measured in both directions.** A system that refuses
everything scores perfectly on leakage and is useless. The gold set contains
positive controls — a counselor *must* reach the 504 file, HR *must* reach the
compensation schedule — paired with the refusal cases they mirror.

> Groundedness, correctness, and confabulation rate require a real generation
> model. The harness measures retrieval and refusal correctness today.

## 3. Security metrics — gates

| Metric | Threshold |
| --- | --- |
| Cross-tenant leakage | **0** |
| Unauthorized retrieval | **0** |
| Prompt injection success | **0** |
| Privilege escalation | **0** |
| Tool authorization bypass | **0** |
| Data exfiltration | **0** |

Any non-zero value blocks release. These are not targets to trend toward.

## 4. System metrics

Latency (p50/p95/p99), throughput, token usage, cost per query, error rate,
retry rate, tool success rate.

Cost per query deserves particular attention in a district: a superintendent
who learns the assistant costs materially per question will use it differently
than one who does not, and the number should be known before that conversation
rather than during it.

## 5. Governance metrics

| Metric | Type |
| --- | --- |
| Approved AI systems | Score |
| **Unapproved systems serving traffic** | **Gate — must be 0** |
| Systems with completed risk assessment | Score |
| **Heightened-scrutiny systems without oversight** | **Gate — must be 0** |
| Overdue reviews | Score, with a threshold |
| Training completion rate | Score, with a target |
| Policy exceptions | Score |
| Incidents | Score |

Computed by `AIRegistry.metrics()`.

## 6. Business metrics

Hours saved, cost saved, cycle-time reduction, adoption, satisfaction, outcome
improvement — recorded via `ModernizationMeasurement`.

`measurement_method` is a **required** field. A saved-hours figure without a
stated method is a marketing claim, and a district presenting one to its board
will be asked how it was derived.

---

## Running the harness

```python
from inflexis.evaluation import EvaluationHarness, load_gold_set

harness = EvaluationHarness(run_query, principals_by_role)
report = harness.run(load_gold_set("governance/evaluation/acme-isd-gold-set.json"))

print(report.summary())
if report.release_blocked:
    raise SystemExit("security failures block release")
```

The harness must be driven through `pipeline.answer()`, not `pipeline.run()`.
`run()` executes one pass and can return a provisional "rewrite" verdict;
evaluating that scores the system on an intermediate state rather than on what
a user would see.

## CI

`.github/workflows/ci.yml` runs the gold set as a **release gate**, separately
from the general test job, so a leakage regression fails visibly rather than
as one line among ninety.

---

## What good looks like for a pilot

| Metric | Target |
| --- | --- |
| Security gates | All zero. Non-negotiable. |
| Refusal correctness | > 95% |
| Authority hit rate (policy questions) | > 90% |
| Freshness hit rate | 100% — superseded content should be structurally unreachable |
| Citation accuracy | > 95% |
| p95 latency | < 3s for hybrid retrieval |

Freshness at 100% is not optimism. Superseded and expired content is excluded
by status and date at the filter level, so anything below 100% indicates an
ingestion or metadata defect, not a ranking one.
