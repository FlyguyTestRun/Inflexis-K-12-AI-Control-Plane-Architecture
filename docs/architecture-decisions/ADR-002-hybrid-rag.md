# ADR-002 — Hybrid BM25 + vector retrieval with RRF is the default

**Status:** accepted
**Date:** 2026-08-26

## Context

District knowledge is unusual in one respect that matters enormously for
retrieval: it is saturated with **exact terminology that carries meaning**.

- `EIC(LOCAL)`, `FNG(LOCAL)` — board policy codes
- `TEC §25.085` — statute citations
- `DAEP`, `FAPE`, `IEP`, `504` — programme acronyms
- `HB 149` — bill numbers
- policy version numbers, effective dates, employee and campus identifiers

A teacher asking "what does EIC(LOCAL) say about class rank" is not asking a
semantic question. They are asking for the document that contains that exact
token. Dense vector retrieval, which is excellent at meaning, is actively bad
at this: it will confidently return three semantically similar attendance
policies, none of which is EIC(LOCAL).

The inverse is equally true. A teacher asking "what happens if a kid keeps
showing up late" shares almost no tokens with a document titled "Campus
Punctuality Expectations." Lexical retrieval misses it entirely.

Districts ask both kinds of question, often in the same sentence.

## Decision

The default retrieval strategy is:

```
BM25  +  vector search
        ↓
       RRF
        ↓
    reranking
        ↓
authority / freshness / ACL validation
        ↓
     generation
```

**BM25** handles exact terminology. The tokenizer is tuned to keep policy codes
intact — `EIC(LOCAL)` and `25.085` survive as single tokens rather than
shattering into `eic`, `local`, `25`, `085`.

**Vector search** handles semantic phrasing.

**Reciprocal Rank Fusion** combines them. RRF is used specifically because BM25
scores and cosine similarities are on incomparable scales; adding or averaging
them is a category error that silently lets whichever retriever produces larger
numbers dominate. RRF discards magnitudes and fuses ranks:

```
score(d) = Σ  1 / (k + rank_i(d))
```

with `k = 60` conventionally. The damping means a document ranked third by both
retrievers can outrank one ranked first by only one — RRF rewards *agreement*,
which is the signal worth having.

**Reranking** then decides which of the fused candidates actually answer the
question, behind a provider interface.

## Consequences

**Good.**

- Exact policy-code lookups work, which is most of what districts actually ask.
- Semantic paraphrase works.
- Retrieval quality degrades gracefully if either retriever is weak.
- RRF requires no score calibration between retrievers, so swapping the
  embedding model does not require re-tuning fusion.

**Costs.**

- Two retrievals per query instead of one: more latency, more cost.
- Two indexes to keep consistent at ingestion.
- `k` and any per-retriever weights are tuning surface that must be exercised
  against a district gold set rather than guessed.

**Not the default, but supported:**

- **GraphRAG** where relationships are the question (policy dependencies,
  multi-hop organisational queries). An optional provider, not a replacement.
  Most district questions are lookups, and a graph adds cost and failure modes
  that a lookup does not need.
- **Agentic RAG** for genuine multi-step research. Reserved for complex
  research because a planner over a simple question is slower, costlier, and
  less predictable than retrieval.

See [`../retrieval/strategy-selection.md`](../retrieval/strategy-selection.md).

## Implementation note

The offline `HashingEmbeddingProvider` is **not** a semantic model — it hashes
tokens deterministically so the pipeline can be tested without a model
endpoint. Every claim in this ADR about semantic recall must be re-established
against a real embedding model before a pilot. This is recorded in
[`../PROJECT_STATE.md`](../PROJECT_STATE.md) as a known limitation.
