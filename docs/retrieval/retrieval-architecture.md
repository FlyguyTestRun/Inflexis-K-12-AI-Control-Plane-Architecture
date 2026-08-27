# Retrieval architecture

The default pipeline, stage by stage, with the reasoning and the tuning
surface.

---

## Pipeline

```
AuthorizedQuery  (authorization already happened — ADR-003)
     │
     ├──────────────┬──────────────┐
     ▼              ▼              ▼
   BM25          vector      (graph, optional)
     │              │              │
     └──────────────┼──────────────┘
                    ▼
                   RRF
                    ▼
             top-N candidates
                    ▼
                reranker
                    ▼
        in-process filter re-check
                    ▼
             corrective check
              ╱          ╲
        sufficient    insufficient
             │             │
             ▼             ▼
         generate    rewrite / broaden /
                     clarify / escalate / refuse
```

---

## Stage 1 — Lexical (BM25)

Okapi BM25 over the chunk store, with the filter applied **during** the scan so
unauthorized chunks are never scored.

**Why lexical matters here.** District knowledge is saturated with exact
terminology that carries meaning: `EIC(LOCAL)`, `TEC §25.085`, `DAEP`, `FAPE`,
`IEP`, `504`, `HB 149`, policy versions, dates, employee IDs. A teacher asking
about `EIC(LOCAL)` wants the document containing that token, and vector search
will confidently return three similar attendance policies that are not it.

**Tokenization is load-bearing.** The pattern
`[A-Za-z0-9]+(?:\.[0-9]+)*(?:\([A-Za-z]+\))?` keeps `EIC(LOCAL)` and `25.085`
intact. A naive tokenizer shatters them into `eic`, `local`, `25`, `085` and
destroys exactly the signal that makes lexical retrieval worth having.

**Tuning:** `k1` (term frequency saturation, default 1.5) and `b` (length
normalisation, default 0.75). `b` is the one worth tuning — district corpora
vary a lot in chunk-length uniformity.

## Stage 2 — Semantic (vector)

Dense retrieval for paraphrase: "what happens if a kid keeps showing up late"
against a document titled "Campus Punctuality Expectations", which shares
almost no tokens.

Embeddings are cached by **content hash**, so a re-indexed but unchanged chunk
reuses its vector and a tampered chunk does not.

> The shipped `HashingEmbeddingProvider` is a deterministic token-hashing
> stand-in, **not a semantic model**. It exists so the pipeline can be tested
> offline. Semantic recall claims must be re-established against a real
> embedding model.

## Stage 3 — Fusion (RRF)

```
score(d) = Σ over lists  weight_i / (k + rank_i(d))
```

**Why rank fusion rather than score fusion.** BM25 scores are unbounded and
corpus-dependent; cosine similarities sit in [-1, 1]. Adding or averaging them
is a category error — whichever retriever happens to produce larger numbers
dominates, and the blend silently changes when you swap the embedding model.
RRF discards magnitudes entirely.

`k = 60` damps the top ranks so a document found at rank 3 by *both*
retrievers can outrank one found at rank 1 by only one. RRF rewards agreement,
which is the signal worth having.

Per-retriever weights are supported and default to unweighted, because
unweighted is the honest starting point before a district's gold set says
otherwise.

## Stage 4 — Reranking

Two implementations behind one interface:

- **`ProviderReranker`** — cross-encoder via a `RerankerProvider`. Production.
- **`HeuristicReranker`** — dependency-free. Offline default and a sane
  fallback when the reranking endpoint is unavailable.

The heuristic scores:

```
coverage × (1 + w_authority · authority + w_freshness · freshness)
```

Two properties are deliberate:

**Multiplicative, not additive.** An additive form gives any current,
authoritative document a score floor around 0.5 regardless of whether it
addresses the question — which disables the corrective gate. Authority and
freshness *amplify* relevance; they never create it.

**Coverage is weighted by term informativeness.** Unweighted coverage counts
`the`, `district`, and `policy` the same as `interplanetary`. That let "what is
the district policy on interplanetary field trips" score as a confident hit
against unrelated board policy. Coverage is now IDF-weighted, and corpus
statistics are **tenant-scoped** — cross-tenant document frequencies would be a
ranking side channel.

Scores land roughly in "fraction of the question this source addresses,
weighted by how much it should be believed", which is what makes an absolute
relevance threshold meaningful at all.

## Stage 5 — Filter re-check

Defence in depth. Anything the backend returned that the filter rejects is
dropped and audited at `SECURITY` severity.

A retriever that *relies* on this re-check is broken: unauthorized rows were
already read out of the datastore. The re-check catches an adapter bug; it is
not the boundary.

## Stage 6 — Corrective check

In order: empty → relevance → freshness → authority → conflict.

| Verdict | Action |
| --- | --- |
| `EMPTY` | rewrite once, then refuse |
| `INSUFFICIENT_RELEVANCE` | rewrite once, then refuse |
| `STALE` | escalate — evidence exists but every piece is expired or superseded |
| `INSUFFICIENT_AUTHORITY` | broaden, then escalate |
| `CONFLICTING` | escalate — do not pick a winner silently |
| `SUFFICIENT` | generate |

**`pipeline.answer()` drives this to a terminal verdict.** `run()` executes one
pass and can return a provisional `REWRITE_QUERY`; handing that to a caller
with no rewriter invites treating "not a refusal" as "go ahead". `answer()`
exhausts the budget and converts it to refuse or escalate.

A rewritten query is **re-authorized through the decision point**, not run
against the existing filter. Our engine computes filters independently of query
text, but that is a property of this engine, not a guarantee of the
`PolicyDecisionPoint` protocol.

---

## Tuning surface

| Parameter | Default | Notes |
| --- | --- | --- |
| `BM25.k1` | 1.5 | Conventional |
| `BM25.b` | 0.75 | Worth tuning; depends on chunk-length uniformity |
| `RRF.k` | 60 | Conventional; lower sharpens top-rank influence |
| `RRF.weights` | unweighted | Tune only with gold-set evidence |
| `candidate_pool` | 50 | Fused candidates passed to the reranker |
| `final_n` | 8 | Evidence passages sent to the model |
| `min_score` | 0.5 | **Reranker-scale dependent.** Calibrated for `HeuristicReranker` against a 15-document synthetic corpus. A provider reranker needs its own calibration and declares `default_min_score = None` to force the question. |
| `require_authority` | off | Per use case, not platform-wide |
| `authority_threshold` | handbook | Used only when the gate is on |
| `max_rewrites` | 1 | Bounded to prevent retry storms |

**Setting `min_score` to 0 disables the relevance gate entirely.** Every
candidate with any positive score becomes "relevant", and a query sharing a
common word with the corpus produces a confident answer. That is the failure
the gate exists to prevent.
