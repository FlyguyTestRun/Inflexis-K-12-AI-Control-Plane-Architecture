# NIST Generative AI Profile (AI 600-1) mapping

The GenAI Profile enumerates risks specific to generative systems. This maps
each to the platform's position, including where that position is "mitigated,
not solved."

---

| Risk | Platform position | Where |
| --- | --- | --- |
| **Confabulation** | Corrective gate: relevance, freshness, authority, conflict checks before generation. Refusal is a correct outcome. Informativeness-weighted relevance prevents a filler-word match from clearing the gate. Every answer carries citations with page or section provenance. | `retrieval/corrective.py` |
| **Dangerous or violent content** | Registration-time screening (`PU-MANIPULATION`, `PU-INCITEMENT`). Read-only corpus of approved district documents. | `governance/texas/policy-controls.json` |
| **Data privacy** | Authorization before retrieval; trust-domain partitioning; entitlements beyond role membership; audit records exclude content. Model approval constrains where content may be sent, independently of user entitlement. | `authz/`, `models/registry.py` |
| **Environmental impact** | Cost and token usage audited per request. Cheapest-approved-model routing. **Not** measured as energy or carbon. | `contracts/audit.py` |
| **Harmful bias and homogenisation** | Required for heightened-scrutiny systems by the risk rubric. **No evaluation harness exists.** This is the largest gap in the mapping. | `governance/risk/` |
| **Human-AI configuration** | Disclosure policy for public-facing systems. Advisory framing with citations. High-impact decisions require human review; heightened-scrutiny systems cannot register without a documented oversight mechanism. | `governance/policies/disclosure-policy.json` |
| **Information integrity** | Content hashes detect corpus tampering. Authority hierarchy weights sources. Version-conflict detection escalates rather than silently choosing. Superseded and expired content excluded from retrieval. | `contracts/document.py`, `retrieval/corrective.py` |
| **Information security** | See [`../security/threat-model.md`](../security/threat-model.md). Authorization is architectural, not prompt-level. | `docs/security/` |
| **Intellectual property** | Provenance on every chunk. District-owned corpus. Model registry records vendor training terms and refuses non-public approval for models that may train on submitted data. | `models/registry.py` |
| **Obscene / CSAM** | Registration screening (`PU-CSAM-SEXUAL-EXPLOITATION`), specified as both a registration screen **and** an output-validation control, because a general-purpose assistant can be steered there regardless of registered purpose. | `governance/texas/policy-controls.json` |
| **Value chain and component integration** | Model, vendor, and tool registries. Zero runtime dependencies in the core library. Preview isolation. | `models/`, `tools/`, ADR-006 |

---

## Where this mapping is weakest

**Harmful bias.** The rubric requires bias evaluation for heightened-scrutiny
systems and nothing implements it. A district registering such a system would
find a policy requirement with no tooling behind it. This is the single most
important gap in the governance implementation.

**Output validation.** The CSAM and obscene-content control is *specified* as
an output-validation control. Output validation is a named pipeline stage in
the architecture but is not implemented — generation currently ends at the
model gateway.

**Environmental impact** is tracked as cost and tokens only. Presenting that as
environmental measurement would be an overclaim.
