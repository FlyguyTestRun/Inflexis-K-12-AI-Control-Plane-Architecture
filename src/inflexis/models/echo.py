"""Offline model provider used by tests and local development.

It does not generate language. It echoes a deterministic, inspectable summary
of what it was given, which makes prompt construction and cost accounting
testable without a model endpoint or an API key.
"""

from __future__ import annotations

from ..contracts.model import Completion


class EchoModelProvider:
    """Deterministic stand-in for a real LLM."""

    def __init__(self, model_id: str = "echo-offline") -> None:
        self.model_id = model_id

    def complete(
        self, prompt: str, *, system: str = "", max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Completion:
        # Rough token proxy; adequate for exercising cost accounting offline.
        input_tokens = max(1, len(prompt) // 4)
        text = f"[offline echo] prompt received with {input_tokens} approx tokens"
        return Completion(
            text=text,
            model_id=self.model_id,
            input_tokens=input_tokens,
            output_tokens=max(1, len(text) // 4),
        )
