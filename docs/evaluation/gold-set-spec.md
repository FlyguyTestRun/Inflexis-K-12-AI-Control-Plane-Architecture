# District gold set specification

Every district pilot needs its own evaluation dataset. Generic benchmark scores
say nothing about whether a system answers *this district's* questions from
*this district's* documents under *this district's* permissions.

Schema: [`../../schemas/gold-case.schema.json`](../../schemas/gold-case.schema.json).
Reference set: [`../../governance/evaluation/acme-isd-gold-set.json`](../../governance/evaluation/acme-isd-gold-set.json).

---

## Case structure

| Field | Purpose |
| --- | --- |
| `query` | The question, in the words a real user would use |
| `as_role` | Who is asking — the same query has different correct answers per role |
| `expected_behaviour` | `answer`, `refuse`, `clarify`, or `escalate` |
| `expected_sources` | Chunk ids that should be retrieved |
| `forbidden_sources` | Chunk ids that must **not** appear |
| `authority_requirement` | Minimum authority level for this question |
| `freshness_required` | Whether stale evidence disqualifies |
| `citation_required` | Whether an answer must carry citations |
| `risk_level` | Severity if the case fails |

---

## Composition

A gold set made only of questions the system should answer measures
helpfulness and nothing else. Aim for roughly:

| Category | Share | Purpose |
| --- | --- | --- |
| Should answer | ~40% | Does it work? |
| **Should refuse (unauthorized)** | ~25% | Does it leak? |
| **Should refuse (no evidence)** | ~15% | Does it confabulate? |
| Freshness and conflict | ~10% | Does it serve stale or contradictory policy? |
| **Positive controls** | ~10% | Is it useful to the people who *are* entitled? |

**Positive controls are not optional.** For every "teacher must not reach the
HR file" case, include "HR *must* reach the HR file". A system that refuses
everything passes every leakage test and is worthless. Both halves must hold,
and only pairing them proves it.

---

## Writing good cases

**Use real questions.** Collect them from the help desk queue, the
superintendent's inbox, and the questions new teachers ask in August. Invented
questions test invented behaviour.

**Use real phrasing.** Staff write "what's the deal with late work" and "can I
get a kid's 504 stuff", not "what is the district policy regarding late work
submission". Retrieval must handle how people actually type.

**Include the lexical cases.** Every district has terminology that must match
exactly: policy codes, programme acronyms, form numbers. These are where pure
vector retrieval fails, and where a district notices.

**Include the cases you are afraid of.** The question a parent might ask under
FOIA. The question a disgruntled employee might ask. The question a curious
student might try. If a case makes you uncomfortable to write down, it belongs
in the set.

**One assertion per case.** A case testing both authorization and freshness
tells you something failed, not what.

---

## Sizing

| Stage | Cases |
| --- | --- |
| Initial pilot | 50-100 |
| Production | 200-500 |
| Per new use case | +30-50 |

Below fifty, the metrics are noise. Beyond a few hundred, maintenance cost
starts to exceed marginal signal unless cases are being retired as they stop
finding bugs.

---

## Maintenance

- **Every production incident becomes a case.** This is the highest-value
  source of cases there is.
- **Every user report of a bad answer becomes a case**, whether or not it turns
  out to be a bug.
- **Review when policy changes.** A board policy amendment can invalidate
  expected answers, and a gold set asserting repealed policy is worse than none.
- **Re-run before every release**, and treat security-gate failures as
  blocking.

---

## Threshold calibration

The relevance floor (`min_score`) must be calibrated **per district and per
reranker**.

The shipped default, `HeuristicReranker.default_min_score = 0.5`, was
calibrated against a 15-document synthetic corpus where genuine matches score
1.2-1.5 and incidental overlap scores below 0.45. Both numbers depend on corpus
size, chunk length, and the reranker in use.

Procedure:

1. Run the district gold set with the gate wide open (`min_score=0`).
2. Record scores for cases that should answer and cases that should refuse.
3. Choose a floor that separates the two populations.
4. Re-run and confirm both halves — no leakage *and* no spurious refusals.

`ProviderReranker` declares `default_min_score = None` deliberately: a vendor
reranker emits scores on its own scale, and guessing a threshold for it would
silently mis-set the gate in one direction or the other. The pipeline forces
the question rather than assuming an answer.
