# Architecture principles

Nine principles. Each is stated as a rule, followed by the failure it prevents,
because a principle without a named failure mode is decoration.

---

## 1. Authorization is computed from identity, never from text

Entitlements derive from the authenticated principal. No code path leads from
query text, document content, or model output to an authorization decision.

**Prevents:** prompt injection escalating privilege. If text cannot influence
entitlement, no phrasing — however clever, however deeply buried in a poisoned
document — can widen access.

**Enforced by:** `PolicyEngine.authorize_retrieval` takes the principal and
ignores the query for entitlement purposes; a test asserts the filter is
byte-identical for benign and hostile queries.

---

## 2. Fail closed

Empty ACL means nobody. Unknown role means no grant. No readable trust domain
means refuse the query rather than run it unscoped. Unregistered AI system
means no traffic. Unregistered tool means denial.

**Prevents:** the misconfiguration that silently grants rather than silently
denies. The failure mode of a tight default is a support ticket; the failure
mode of a loose one is a FERPA incident.

---

## 3. Make invariants structural, not documentary

Where a rule can be enforced by a type, a contract invariant, or a capability
token, enforce it there rather than in a code-review checklist.

**Prevents:** decay. "Always pass the filter" survives about six months and
three new engineers. `AuthorizedQuery` being unforgeable survives indefinitely.

**Examples:** retrievers cannot be called without proof of authorization;
`ToolDescriptor` refuses to construct a high-risk write tool with no human
approval; `AISystemRecord` refuses a heightened-scrutiny system with no
documented oversight.

---

## 4. Refusal is a correct outcome

"I do not have good enough evidence to answer that" is a success, not an error.
The system never invents evidence and never lowers its own bar to produce an
answer.

**Prevents:** confident wrong answers about student discipline, special
education, or policy — the failure that ends a district pilot and deserves to.

**Measured by:** refusal correctness in the gold set. A case whose right answer
is a refusal fails if the system answers, however fluent the answer.

---

## 5. Evidence carries provenance or it is not evidence

Every chunk carries source system, source URI, content hash, and where
applicable page, section, table, or image identifier, plus whether the text was
read or inferred by OCR/vision.

**Prevents:** an answer nobody can check. A district cannot act on "the policy
says X" without knowing which policy, which version, and which page.

---

## 6. Separate what you are asking about

Trust domain (where it lives), data classification (how to handle it),
authority (how much to believe it), and status (whether it is current) are four
axes, not one sensitivity number.

**Prevents:** the collapsed design that either over-restricts public board
policy or under-protects a low-authority document containing student names.

---

## 7. Governance on the request path

The AI registry gates production traffic. Risk classification is a contract
invariant. Rejected systems stay in the inventory as evidence.

**Prevents:** inventory drift — the spreadsheet that stops matching reality the
first time someone stands up a pilot that becomes load-bearing.

---

## 8. Least privilege, and start read-only

Tools declare their full posture before registration. Write tools are declared
without implementations until the read-only layers are stable. Agents see only
the tools the *caller* may invoke. Credentials are scoped per tool.

**Prevents:** excessive agency. An agent that can only read cannot do
irreversible damage while the platform is still learning its failure modes.

---

## 9. State limits plainly

The offline embedder is not semantic. Thresholds are calibrated against a
15-document synthetic corpus. Conflict detection is structural, not semantic.
Governance rows built from secondary sources say so and cannot assert
applicability.

**Prevents:** the most damaging failure available to a governance product —
a district believing that installing software made it compliant, and skipping
the legal review only its counsel can perform.

---

## Applying these to a new component

Before merging a component that touches retrieval, tools, or models:

1. Can it be reached without an authorization decision? (Principle 1, 3)
2. What does it do when its input is missing or malformed? (Principle 2)
3. Can its guarantee be expressed as a type or invariant? (Principle 3)
4. What does it do when it has insufficient evidence? (Principle 4)
5. Does everything it returns carry provenance? (Principle 5)
6. Is it audited, and does the audit record exclude content? (Architecture §11)
7. What does it claim that has not been verified? (Principle 9)
