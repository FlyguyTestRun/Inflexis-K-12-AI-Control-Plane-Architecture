"""Model gateway contracts (Plane 5).

No component outside :mod:`inflexis.models` may import a vendor SDK. Everything
goes through these protocols so that a district can run Azure OpenAI, a
self-hosted model, or a future provider without touching retrieval, governance,
or application code (ADR-005).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Sequence


class ModelKind(str, Enum):
    LLM = "llm"
    VLM = "vlm"
    EMBEDDING = "embedding"
    RERANKER = "reranker"


class Lifecycle(str, Enum):
    """Vendor API lifecycle stage. Drives ADR-006 preview isolation."""

    GA = "ga"
    PREVIEW = "preview"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    """Registry entry for one model. The unit of governance for Plane 5."""

    model_id: str
    kind: ModelKind
    provider: str
    lifecycle: Lifecycle = Lifecycle.GA
    #: Cost per million tokens, used by the FinOps and routing layers.
    input_cost_per_mtok: float = 0.0
    output_cost_per_mtok: float = 0.0
    max_context_tokens: int = 0
    #: Trust domains this model is approved to process. A model that has not
    #: been approved for student-confidential data must not receive it, even
    #: if the caller is authorized to see that data.
    approved_trust_domains: frozenset[str] = field(default_factory=frozenset)
    #: Set when the vendor may train on submitted data. Such a model must never
    #: be routed content above PUBLIC classification.
    vendor_may_train_on_data: bool = False
    data_residency: str = "unspecified"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.vendor_may_train_on_data and self.approved_trust_domains - {
            "A_public"
        }:
            raise ValueError(
                f"model {self.model_id!r} allows vendor training but is approved "
                "for non-public trust domains; this combination is prohibited"
            )


@dataclass(frozen=True, slots=True)
class Completion:
    text: str
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"

    def cost(self, descriptor: ModelDescriptor) -> float:
        return (
            self.input_tokens / 1_000_000 * descriptor.input_cost_per_mtok
            + self.output_tokens / 1_000_000 * descriptor.output_cost_per_mtok
        )


class ModelProvider(Protocol):
    """Text generation."""

    def complete(
        self, prompt: str, *, system: str = "", max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion: ...


class EmbeddingProvider(Protocol):
    """Dense vector embedding."""

    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class RerankerProvider(Protocol):
    """Cross-encoder style relevance scoring of candidates against a query."""

    def rerank(
        self, query: str, documents: Sequence[str], *, top_n: int | None = None
    ) -> list[tuple[int, float]]:
        """Return ``(original_index, relevance_score)`` best-first."""
        ...


class VisionProvider(Protocol):
    """Image and document-page understanding for multimodal ingestion."""

    def describe(self, image_bytes: bytes, *, prompt: str = "") -> Completion: ...
