# Azure: GA versus preview

Operationalising
[ADR-006](../architecture-decisions/ADR-006-preview-feature-isolation.md) for
the Azure reference deployment.

---

## Why this document exists

The most useful Azure AI capabilities frequently arrive in preview. The failure
is not using them — it is using them *without noticing*, so that a district's
production assistant ends up depending on an endpoint with no availability
commitment and terms that may differ from the GA service, and nobody ever
decided that.

For a district this matters more than for a startup: the district has a
procurement process that approved a set of services and a security review that
assessed them.

---

## Classification

Verify current lifecycle stage against Microsoft's documentation before
relying on any row. This table records *how to treat* each capability class,
not a claim about its status today — statuses change, and this document will
drift.

| Capability | Treat as | Notes |
| --- | --- | --- |
| Azure AI Search — keyword / BM25 | **Production baseline** | Long-stable core |
| Azure AI Search — vector search | **Production baseline** | |
| Azure AI Search — hybrid + RRF | **Production baseline** | Confirm scoring matches our contract |
| Azure AI Search — semantic ranker | Production, tier-dependent | Check pricing tier availability |
| Azure AI Search — **agentic retrieval** | **Verify before use** | Newer capability; confirm lifecycle before any production dependency |
| Azure OpenAI — GA model deployments | **Production baseline** | Pin API version explicitly |
| Azure OpenAI — newest model previews | **Preview** | Register with `lifecycle: preview` |
| Microsoft Foundry capabilities | **Verify individually** | Mixed lifecycle surface |
| Entra ID auth | **Production baseline** | |
| Key Vault, Storage, PostgreSQL, Monitor | **Production baseline** | |

---

## Rules

1. **Default routing selects GA only.** `ModelRegistry.select()` excludes
   preview unless the caller passes `allow_preview=True`.
2. **Declare the lifecycle.** `ModelDescriptor.lifecycle` is required.
3. **Every preview dependency has a GA fallback**, and the fallback is tested,
   not hypothetical.
4. **Record it in the registry entry** so it surfaces at approval and at every
   review.
5. **Pin API versions.** Never float to "latest" in production.
6. **Re-check lifecycle at every scheduled review**, because vendor status
   changes and stale lifecycle metadata is worse than none — it is trusted.

---

## Reporting

```python
for model in registry.preview_models():
    print(model.model_id, model.provider, model.notes)
```

A district can be told accurately which parts of its deployment rest on preview
terms. This question comes up in security review and most vendors cannot answer
it.

---

## Agentic retrieval specifically

Azure AI Search's agentic retrieval is attractive: it moves query planning and
decomposition into the search service.

Two reasons to be deliberate before adopting it:

**Lifecycle.** Confirm its current stage. If preview, it is a Phase 3
experiment behind `allow_preview`, not a Phase 1 dependency.

**Authorization.** Any service-side planner must apply our `RetrievalFilter` to
every sub-query it generates, not merely to the initial one. A planner that
decomposes a question into three searches and filters only the first has
defeated ADR-003 in a way that is invisible in testing until someone asks the
right question.

Verify that property explicitly before adoption. It is the kind of thing that
is easy to assume and expensive to be wrong about.
