"""Model registry and routing.

Routing decisions are made against *declared model properties*, not against a
hard-coded vendor list. The property that matters most is
``approved_trust_domains``: a model that has not been approved for
student-confidential content must not receive it even when the requesting user
is fully entitled to read that content. Entitlement governs what a person may
see; model approval governs where that content may be sent.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from ..contracts.classification import TrustDomain
from ..contracts.model import Lifecycle, ModelDescriptor, ModelKind


class ModelRoutingError(RuntimeError):
    """Raised when no approved model can serve a request."""


class ModelRegistry:
    """The approved model inventory."""

    def __init__(self, descriptors: Iterable[ModelDescriptor] = ()) -> None:
        self._models: dict[str, ModelDescriptor] = {}
        for descriptor in descriptors:
            self.register(descriptor)

    def register(self, descriptor: ModelDescriptor) -> None:
        self._models[descriptor.model_id] = descriptor

    def get(self, model_id: str) -> ModelDescriptor | None:
        return self._models.get(model_id)

    def __iter__(self) -> Iterator[ModelDescriptor]:
        return iter(self._models.values())

    def preview_models(self) -> list[ModelDescriptor]:
        """Models on preview APIs -- reported so ADR-006 stays enforceable."""
        return [m for m in self._models.values() if m.lifecycle is Lifecycle.PREVIEW]

    def select(
        self,
        kind: ModelKind,
        *,
        required_domains: frozenset[TrustDomain] = frozenset(),
        allow_preview: bool = False,
        prefer_cheapest: bool = True,
    ) -> ModelDescriptor:
        """Choose an approved model, or raise.

        Failing loudly is deliberate. Silently falling back to a model that is
        not approved for the data in hand is the exact failure this registry
        exists to prevent.
        """
        needed = {d.value for d in required_domains}
        candidates = [
            m
            for m in self._models.values()
            if m.kind is kind
            and m.lifecycle not in (Lifecycle.RETIRED, Lifecycle.DEPRECATED)
            and needed <= m.approved_trust_domains
            and (allow_preview or m.lifecycle is Lifecycle.GA)
        ]
        if not candidates:
            raise ModelRoutingError(
                f"no approved {kind.value} model covers trust domains "
                f"{sorted(needed) or ['(none)']}"
                + ("" if allow_preview else " using GA endpoints only")
            )
        if prefer_cheapest:
            candidates.sort(
                key=lambda m: (m.input_cost_per_mtok + m.output_cost_per_mtok)
            )
        return candidates[0]
