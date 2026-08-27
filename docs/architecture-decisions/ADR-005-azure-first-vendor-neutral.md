# ADR-005 — Azure is the reference deployment; interfaces stay portable

**Status:** accepted
**Date:** 2026-08-26

## Context

Texas school districts are overwhelmingly Microsoft shops. Entra ID for
identity, Microsoft 365 for documents, existing Azure agreements, existing
security review processes, and staff who already know the tooling. Deploying
anywhere else means fighting the district's procurement, its security team, and
its habits simultaneously.

At the same time, a platform intended to serve many districts over many years
cannot weld itself to one vendor's product decisions. Vendors deprecate APIs,
change pricing, move features between tiers, and occasionally retire a service
a district depends on. A district may also arrive with a genuine constraint —
a data residency requirement, an existing search investment, a self-hosting
mandate.

These pull in opposite directions and both are real.

## Decision

**Azure is the reference deployment. Vendor coupling is confined to adapters.**

Reference stack: Entra ID, Azure OpenAI / Microsoft Foundry, Azure AI Search,
Azure Storage, PostgreSQL, Redis where warranted, Azure Monitor, Key Vault,
Azure Container Apps or AKS.

Portability is enforced structurally rather than promised:

- The core library has **zero runtime dependencies**. Vendor SDKs live in
  optional extras. You cannot accidentally couple to a vendor whose SDK is not
  imported.
- Every vendor-facing capability sits behind a protocol in
  `contracts/`: `ModelProvider`, `EmbeddingProvider`, `RerankerProvider`,
  `VisionProvider`, `Retriever`, `AuditSink`.
- Only `inflexis.models` may import a model vendor SDK.
- A working non-Azure implementation of each interface ships and is exercised
  by the test suite. This is the part that matters: an interface with exactly
  one implementation is not an abstraction, it is a vendor wrapper with extra
  steps. The offline implementations are what prove the seam is real.

## What is *not* abstracted

Being honest about the limits keeps the claim credible:

- **Filter pushdown is required.** A retrieval backend that cannot apply
  `RetrievalFilter` server-side is not usable under ADR-003. This genuinely
  narrows vendor choice, and that is the intended trade.
- **Identity assumes OIDC/SAML-shaped claims.** A district on something exotic
  needs adapter work.
- **Trust-domain partitioning assumes the backend can partition.** A single
  flat index with no filtering is out.

## Consequences

**Good.**

- Lands inside a district's existing procurement, security, and skills.
- A vendor change is an adapter change, not a rewrite.
- The full test suite runs with no cloud credentials, which is what makes CI
  and phone-driven development possible.

**Costs.**

- Interfaces are more work than calling the SDK directly, and occasionally
  cannot express a vendor's best feature. Where that bites, ADR-006 governs
  whether to reach for it.
- Two implementations of everything to maintain.
- The offline implementations are reference-grade, not production-grade, and
  the documentation must keep saying so.
