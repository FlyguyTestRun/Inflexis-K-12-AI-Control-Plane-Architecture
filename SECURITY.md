# Security

This platform handles student education records, personnel records, and
district operational data. Security properties are the product, not a feature
of it.

---

## Reporting a vulnerability

Report privately to the Inflexis Technologies security contact. Do not open a
public issue.

Include: affected component, reproduction steps, the boundary crossed, and
whether real district data was involved. If real data was involved, say so
first — that changes the response path.

---

## Security model in one page

**Authorization precedes retrieval, and it is structural.** Retrievers accept
an `AuthorizedQuery` that only a policy decision point can construct. No
unauthorized content enters model context.

**Authorization never reads text.** Entitlements are computed from the
authenticated principal. There is no code path from query content, document
content, or model output to an entitlement — which is why prompt injection
cannot escalate privilege.

**Tenant is a hard predicate.** No configuration, role, or policy widens a
query across districts. There is no platform-admin bypass.

**Fail closed everywhere.** Empty ACL means nobody. Unknown role means no
grant. No readable domain means refuse rather than run unscoped.

**Model output is untrusted.** It authorizes nothing. A tool call a model
proposes is authorized against the *caller's* principal.

Full detail: [`docs/security/threat-model.md`](docs/security/threat-model.md)
and [`docs/security/trust-boundaries.md`](docs/security/trust-boundaries.md).

---

## Trust domains

| Domain | Access |
| --- | --- |
| A Public | Everyone, including anonymous |
| B District internal | Authenticated staff |
| C Personnel / HR | HR / superintendent **with** `retrieve.personnel` |
| D Student confidential | Counselor / principal / superintendent **with** `retrieve.student` |
| E Highly sensitive / SpEd | Dedicated approved use case only |
| F Legal / privileged | **No general-purpose grant** |
| G Security / credentials | **No general-purpose grant** |

Role membership alone is never sufficient for C, D, or E.

---

## Repository rules

**No secrets.** No keys, tokens, connection strings, or private keys.
Enforced by `scripts/check_repository_hygiene.py`, which fails the build.

**No real data.** All fixtures are synthetic. Acme ISD and Bravo ISD are
invented. The hygiene check rejects real-identifier patterns.

**No silent control erosion.** The hygiene check fails the build on suppressed
security lint, allow-all flags, authorization-bypass identifiers, disabled TLS
verification, and skip/xfail markers inside `tests/security`.

---

## CI gates

| Gate | Blocks on |
| --- | --- |
| Authorization boundary tests | Any failure |
| Gold set | Any security-metric failure |
| Repository hygiene | Secrets, real-data patterns, control erosion |
| Lint and tests | Any failure |

Security metrics are not averaged into an aggregate score. A single
cross-tenant leak is not offset by good recall.

---

## Known gaps

Stated because a security document claiming full coverage is not credible:

- **Output validation is not implemented.** Generation ends at the model
  gateway.
- **Quotas and rate limits are not enforced.** Cost is measured, not capped.
- **Bias evaluation has no harness**, despite being required by the risk rubric
  for heightened-scrutiny systems.
- **No incident response workflow.** Incidents are detected and audited; triage
  and closure are manual.
- **Semantic contradiction is undetected.** Conflict detection is structural.

## Out of scope

- A compromised identity provider. If Entra ID asserts someone is the
  superintendent, the platform believes it.
- A malicious insider with legitimate entitlements. Audit provides detection,
  not prevention.
- Content ingested with the wrong trust domain. Ingestion governance owns this.
- A compromised model provider. Mitigated contractually, not technically.
