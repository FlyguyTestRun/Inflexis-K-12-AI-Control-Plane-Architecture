# Choosing a retrieval strategy

Five strategies behind one orchestration abstraction. They are not five
products, and four of them are not the default.

---

## Decision guide

```
Is the question a lookup against district documents?
    └─ YES ──► HYBRID RAG            ◄── the default, ~most questions
    └─ NO
         │
Does answering require traversing relationships between entities?
    └─ YES ──► GRAPH RAG
         │
Does answering require several dependent steps across different sources?
    └─ YES ──► AGENTIC RAG
         │
Is the answer in a scan, a table, a chart, or a diagram?
    └─ YES ──► MULTIMODAL ingestion + HYBRID retrieval
```

---

## Hybrid RAG — the default

**Use for:** policy questions, procedure lookups, handbook questions,
operational questions, "what does X say about Y".

**Why default:** it covers the overwhelming majority of what districts
actually ask, at one round trip and predictable cost. See
[ADR-002](../architecture-decisions/ADR-002-hybrid-rag.md).

**Examples**
- "What does EIC(LOCAL) say about class ranking?"
- "How many grades per nine-week period?"
- "Who approves a $4,000 requisition?"

---

## GraphRAG — when relationships *are* the question

**Use for:** policy dependency chains, organisational responsibility,
multi-hop entity questions, system dependency mapping.

**Do not use for:** ordinary lookups. A graph adds ingestion cost, an entity
resolution problem, and new failure modes that a lookup does not need. Most
district questions are lookups.

**The honest test:** if you can answer it by finding one document, you do not
need a graph.

**Examples that justify it**
- "Which campus procedures depend on the board policy we are about to amend?"
- "Who is responsible for the systems that touch student attendance data?"

**Status:** not implemented. Phase 2.5, as an optional `Retriever`.

---

## Agentic RAG — for genuine research

**Use for:** questions requiring decomposition, multiple sources, and
reasoning across intermediate results.

**Do not use for:** anything hybrid retrieval answers. A planner over a simple
question is slower, costlier, less predictable, and adds an injection surface.

**Constraints when it does ship**
- Read-only tools only, initially.
- Every tool authorized per invocation against the **caller's** principal.
- Planner sees only tools the caller may invoke.
- Bounded steps and bounded cost.

**Example that justifies it:** "Compare our attendance intervention procedures
against the state requirements, and identify where our campus practices differ
from district policy." — decomposition, multiple sources, synthesis.

**Status:** not implemented. Phase 3.

---

## Multimodal — when the answer is not text

District knowledge is not text-only: scanned board minutes, budget tables,
org charts, facility diagrams.

**Requirements**
- OCR and vision output carries `extraction_method` so downstream consumers
  can weight and label it — an OCR'd figure is not the same evidence as a
  parsed number.
- Page, table, and image identifiers preserved for citation.
- Same authorization path. Multimodal ingestion changes what is retrievable,
  never who may retrieve it.

**Status:** not implemented. Phase 2.

---

## Cost and latency

| Strategy | Round trips | Relative cost | Predictability |
| --- | --- | --- | --- |
| Hybrid | 2 retrievals + 1 rerank | 1× | High |
| + Graph | +1 traversal | ~1.5× | High |
| Multimodal | Ingest-time cost | 1× at query | High |
| Agentic | N steps, unbounded without limits | 5-20× | **Low** |

The predictability column is the one that matters for a district. A
superintendent asking a policy question should not wait fifteen seconds and
incur twenty model calls because a planner decided to be thorough.
