# Trust boundaries

What is trusted, what is not, and where the lines are drawn.

---

## 1. The trust classification

| Input | Trust | Why |
| --- | --- | --- |
| Validated identity token claims | **Trusted** | Cryptographically verified by the IdP |
| Tenant configuration | **Trusted** | Changed only through governed admin paths, audited |
| Policy engine output (`RetrievalFilter`) | **Trusted** | Computed by the control plane from trusted inputs |
| User query text | **Untrusted** | The user may be adversarial, or repeating something adversarial |
| Retrieved document content | **Untrusted** | Anyone who can get text into the corpus can plant instructions |
| Web / external tool output | **Untrusted** | Attacker-controllable by definition |
| Model output | **Untrusted** | A text generator, not an oracle and not an authority |
| Tool arguments proposed by a model | **Untrusted** | Derived from untrusted text |

The single most important line: **model output is untrusted input to
everything downstream**. It is never consulted for an authorization decision.

---

## 2. Boundary crossings

```
   ┌───────────────────────────────────────────────────────┐
   │ IdP (Entra ID)                                        │
   └──────────────────┬────────────────────────────────────┘
                      │ ① verified token
   ┌──────────────────▼────────────────────────────────────┐
   │ CONTROL PLANE                    (trusted)            │
   │   identity → policy engine → RetrievalFilter          │
   └──────────────────┬────────────────────────────────────┘
                      │ ② AuthorizedQuery (filter attached)
   ┌──────────────────▼────────────────────────────────────┐
   │ RETRIEVAL BACKEND                                     │
   │   filter pushed down; only permitted rows are read    │
   └──────────────────┬────────────────────────────────────┘
                      │ ③ chunks (untrusted CONTENT,
                      │    trusted METADATA)
   ┌──────────────────▼────────────────────────────────────┐
   │ IN-PROCESS RE-CHECK          ← defence in depth       │
   │   drop anything the filter rejects; audit as SECURITY │
   └──────────────────┬────────────────────────────────────┘
                      │ ④ authorized evidence
   ┌──────────────────▼────────────────────────────────────┐
   │ MODEL GATEWAY                                         │
   │   content wrapped in untrusted markers                │
   │   model approval checked against content domains      │
   └──────────────────┬────────────────────────────────────┘
                      │ ⑤ completion (untrusted)
   ┌──────────────────▼────────────────────────────────────┐
   │ OUTPUT VALIDATION → citations → response → audit      │
   └───────────────────────────────────────────────────────┘
```

**Crossing ①** — the only place a principal is created. Everything downstream
treats `Principal` as trusted; nothing else may construct one.

**Crossing ②** — the only place an `AuthorizedQuery` is minted. Structurally
enforced: the constructor raises unless the caller holds the policy engine's
private capability token.

**Crossing ③** — the subtle one. Chunk *metadata* (tenant, ACL, trust domain)
is trusted because ingestion set it under governance. Chunk *text* is
untrusted, because a document is a thing people write.

**Crossing ⑤** — model output re-enters as untrusted. It may be shown to a
user with citations; it may not authorize anything, and a tool call it proposes
is authorized against the *caller's* principal, never the agent's.

---

## 3. Trust domains

| Domain | Contents | Reachable by |
| --- | --- | --- |
| A Public | Board policy, public handbooks | Everyone including anonymous |
| B District internal | SOPs, procedures, internal docs | Authenticated staff |
| C Personnel / HR | Compensation, grievances, personnel files | HR / superintendent **with** `retrieve.personnel` |
| D Student confidential | Records, discipline, accommodations | Counselor / principal / superintendent **with** `retrieve.student` |
| E Highly sensitive / SpEd | Special education case files | Dedicated approved use case only |
| F Legal / privileged | Counsel communications | **No general-purpose grant** |
| G Security / credentials | Security config, secrets | **No general-purpose grant** |

F and G are excluded from every role grant by
`RESTRICTED_BY_DEFAULT`. Reaching them requires a separately approved use case
with its own risk assessment — not a role, not a permission, not a
configuration flag.

Grants are additionally intersected with the tenant's *provisioned* domains, so
a misconfigured role in one district cannot reach a domain that district never
enabled.

---

## 4. Secrets

**Never in the repository.** No credentials, Azure keys, Entra secrets,
connection strings, or private keys — enforced by
`scripts/check_repository_hygiene.py`, which fails the build rather than
warning.

Production secrets live in Key Vault, referenced by identity, never by value.
Tool credentials are scoped per tool (`credential_scope`) so a compromised tool
cannot use another tool's authority.

---

## 5. Data

**No real district data in this repository.** All fixtures are synthetic —
Acme ISD and Bravo ISD are invented, as is every document, person, campus, and
policy code in them.

The hygiene check rejects content shaped like real identifiers (SSN patterns,
references to real identifier fields).

For production: student and personnel data stays in the district's tenant, in
its trust domain, in its region. Audit records reference it by identifier and
hash; they never copy it.

---

## 6. What the platform does not defend against

Stating these plainly, because a threat model that claims total coverage is
not credible:

- **A compromised identity provider.** If Entra ID issues a token asserting
  someone is the superintendent, the platform believes it. Mitigation is the
  district's IdP security posture, not ours.
- **A malicious insider with legitimate entitlements.** An HR user entitled to
  personnel files can read personnel files. Audit provides detection, not
  prevention.
- **Ingestion of mislabelled content.** If a student record is ingested with a
  public trust domain, it is retrievable as public content. Mitigation is
  ingestion governance and the ACL validation at index time — which catches
  empty ACLs, not wrong ones.
- **A compromised model provider.** Content sent to an approved model is
  subject to that vendor's security. Mitigation is model approval,
  no-training terms, and data residency — contractual, not technical.
