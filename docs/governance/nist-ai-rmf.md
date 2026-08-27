# NIST AI Risk Management Framework mapping

Mapping the four NIST AI RMF functions — GOVERN, MAP, MEASURE, MANAGE — onto
platform controls.

NIST AI RMF matters here beyond its own merits: secondary sources indicate SB
1964 directs DIR toward a statewide AI code of ethics **modelled on the NIST AI
RMF**. Aligning to it is therefore both good practice and likely to align with
where Texas guidance lands.

Where a subcategory is not implemented, this document says so. A mapping that
claims full coverage is not a mapping, it is marketing.

---

## GOVERN — cross-cutting

| Subcategory theme | Control | Where | Status |
| --- | --- | --- | --- |
| Policies and procedures exist | Versioned AUP and disclosure policy bound to each AI system via `policy_version` | `governance/policies/` | Implemented |
| Accountability structures | `owner`, `business_owner`, `technical_owner` required on every registry record | `contracts/governance.py` | Implemented |
| AI inventory | `AIRegistry` gates production traffic on registration | `governance/registry.py` | Implemented |
| Risk tolerance defined | Risk rubric with per-class required controls | `governance/risk/risk-classification.json` | Implemented |
| Workforce capability | Training assignment, completion, expiration tracking | `TrainingRecord`, `governance/training/` | Implemented |
| Third-party risk | Model and vendor registry with lifecycle and training terms | `models/registry.py` | Implemented |
| Decommissioning | `DeploymentStatus.DECOMMISSIONED`; rejected systems retained as evidence | `contracts/governance.py` | Partial — no decommissioning *workflow* |
| Incident response | `AuditEventType.INCIDENT` defined | `contracts/audit.py` | **Contract only** — no workflow |

---

## MAP — context and risk identification

| Subcategory theme | Control | Where | Status |
| --- | --- | --- | --- |
| Intended purpose documented | `purpose`, `use_case`, `affected_users`, `affected_population` required | `contracts/governance.py` | Implemented |
| System categorised | Four-dimension risk rubric; highest triggered class wins | `governance/risk/` | Implemented |
| Capabilities and limitations | Documented per component; limitations stated in `PROJECT_STATE.md` | `docs/` | Implemented |
| Impacts to individuals characterised | Heightened-scrutiny classification; impact assessment required for that class | `governance/risk/` | Partial — no impact-assessment artifact template |
| Data provenance | `Provenance` on every chunk with source, hash, extraction method | `contracts/document.py` | Implemented |
| Prohibited uses identified | Registration-time screening controls | `governance/texas/policy-controls.json` | Implemented |

---

## MEASURE — analysis and tracking

| Subcategory theme | Control | Where | Status |
| --- | --- | --- | --- |
| Appropriate methods identified | Six metric families | `docs/evaluation/evaluation-framework.md` | Implemented |
| Trustworthiness evaluated | Groundedness, citation accuracy, refusal correctness, confabulation rate | `evaluation/harness.py` | Partial — retrieval and refusal implemented; generation metrics need a real model |
| Safety and security measured | Leakage, injection, privilege escalation, tool bypass | `tests/security/`, gold set | Implemented |
| Privacy risk measured | Cross-tenant and unauthorized-retrieval counters as release blockers | `SecurityMetrics` | Implemented |
| Bias and fairness measured | Required for heightened-scrutiny class | `governance/risk/` | **Not implemented** — required by policy, no harness |
| Feedback gathered | — | — | **Not implemented** |
| Performance monitored in deployment | Latency, tokens, cost audited per request | `contracts/audit.py` | Partial — measured, no dashboards or alerting |

---

## MANAGE — response and treatment

| Subcategory theme | Control | Where | Status |
| --- | --- | --- | --- |
| Risks prioritised and acted on | Risk class determines required controls; prohibited class blocks registration | `governance/` | Implemented |
| High-impact decisions kept human | Heightened-scrutiny systems cannot register without documented oversight; autonomy excluded from high-impact domains | `contracts/governance.py` | Implemented |
| Least privilege for tools | Full tool posture declaration; per-invocation authorization; read-only first | `tools/` | Implemented |
| Third-party risk managed | Approved trust domains constrain routing; preview isolation | `models/` | Implemented |
| Incidents documented and communicated | Filter violations audited at SECURITY severity | `retrieval/pipeline.py` | Partial — detection without a response workflow |
| Regular review | Overdue-review detection; approval without a review date counts as overdue | `governance/registry.py` | Implemented |

---

## Honest gaps

Five, listed so they are visible rather than buried in "partial":

1. **Bias and fairness evaluation.** The risk rubric *requires* it for
   heightened-scrutiny systems. No harness exists. A district registering such
   a system today would have a policy requirement with no tooling behind it.
2. **Incident response workflow.** Incidents are detected and audited. There is
   no triage, escalation, notification, or closure workflow.
3. **Impact assessment artifact.** Required by the rubric; no template or
   structured record type.
4. **Feedback collection.** No mechanism for users to flag a bad answer, which
   is the cheapest source of real evaluation signal a pilot has.
5. **Generation-quality metrics.** Groundedness and confabulation rate need a
   real model to measure meaningfully. The harness measures retrieval and
   refusal correctness today.
