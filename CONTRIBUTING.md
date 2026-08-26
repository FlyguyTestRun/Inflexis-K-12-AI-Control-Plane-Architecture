# Contributing

---

## Setup

```bash
pip install -e ".[dev]"
pytest -q
```

No cloud credentials, no network, no vendor accounts. If a change cannot be
tested that way, it belongs behind an interface with an offline implementation.

---

## Before opening a pull request

```bash
pytest -q
ruff check src tests scripts
python scripts/check_repository_hygiene.py
python scripts/validate_json.py
```

---

## The rules that will get a PR rejected

1. Weakening an authorization control to make a test pass.
2. Real student, personnel, or district data in any fixture.
3. Secrets of any kind.
4. A bypass flag — `allow_all`, admin override, "temporary" test escape.
5. Query text, document content, or model output influencing authorization.
6. A legal conclusion stated in the repository's own voice.
7. A suppressed security lint instead of a fix.
8. A change to an ADR decision without a new ADR.

---

## What a good PR looks like

**Small.** One decision per PR. A PR that changes the entitlement model *and*
adds a retriever is two PRs.

**Tested at the boundary.** If it touches authorization, retrieval filtering,
tenancy, or tool registration, it needs a test of the boundary it could break —
not just a unit test of the new code.

**Documented where it matters.** A new architectural decision gets an ADR. A
non-obvious trade-off gets an entry in
[`docs/DECISION_LOG.md`](docs/DECISION_LOG.md). A new limitation gets added to
[`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md).

**Honest about what it does not do.** A partial implementation is welcome; a
partial implementation described as complete is not.

---

## Commit messages

Explain **why**, not what — the diff shows what.

```
Weight relevance coverage by term informativeness

Unweighted coverage counted "the", "district", and "policy" equally with
"interplanetary", so a question the corpus does not address scored as a
confident hit against unrelated board policy.

Corpus statistics are tenant-scoped: cross-tenant document frequencies
would let one district's corpus composition influence another district's
ranking.
```

---

## Code style

- Comments explain reasoning and trade-offs, never mechanics. A comment that
  restates the line below it should be deleted.
- Module and public-class docstrings say what the component is for and what
  failure it prevents.
- Type hints throughout; `from __future__ import annotations`.
- Frozen dataclasses for contracts.
- No runtime dependencies in the core library. Only `inflexis.models` may
  import a model vendor SDK.
- Line length 100.

---

## Adding a governance requirement

1. Add a row to `governance/texas/applicability-matrix.json` with a citation
   URL.
2. Set `verification_status` honestly. `secondary_source_only` if you did not
   read primary text.
3. Default `district_applicability` to `requires_legal_review`.
4. Name the control in `required_control` and where it lives in
   `implemented_by`.
5. Describe the evidence a district could produce.

A test enforces that unverified rows cannot assert `applies`.

---

## Adding a retriever

Implement `Retriever`. It receives an `AuthorizedQuery` and **must apply
`query.filter` inside the backend query**.

A retriever that fetches and then filters has already read unauthorized rows
out of the datastore. The pipeline's in-process re-check will catch the
leakage, but by then the read happened — the re-check is defence in depth, not
the boundary.

Run the existing security suite against your adapter. It is written to be
reusable for exactly this.
