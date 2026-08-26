"""Evaluation contracts.

"The chatbot sounds good" is not a measurement. These contracts define the gold
set and the metric surface described in ``docs/evaluation/evaluation-framework.md``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from .classification import AuthorityLevel
from .identity import Role


class ExpectedBehaviour(StrEnum):
    """What a correct system does with this case."""

    ANSWER = "answer"
    #: Correct behaviour is to refuse -- no authorized evidence exists.
    REFUSE = "refuse"
    #: Correct behaviour is to ask a clarifying question.
    CLARIFY = "clarify"
    #: Correct behaviour is to route to a human.
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class GoldCase:
    """One district evaluation case."""

    case_id: str
    query: str
    as_role: Role
    expected_behaviour: ExpectedBehaviour = ExpectedBehaviour.ANSWER
    expected_sources: frozenset[str] = field(default_factory=frozenset)
    #: Chunk ids that must NOT appear -- the leakage half of the gold set.
    forbidden_sources: frozenset[str] = field(default_factory=frozenset)
    expected_answer_contains: tuple[str, ...] = ()
    authority_requirement: AuthorityLevel | None = None
    freshness_required: bool = True
    citation_required: bool = True
    risk_level: str = "low"
    tenant_id: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    recall_at_k: float = 0.0
    precision_at_k: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    hit_rate: float = 0.0
    authority_hit_rate: float = 0.0
    freshness_hit_rate: float = 0.0


@dataclass(frozen=True, slots=True)
class SecurityMetrics:
    """Any non-zero value here is a release blocker, not a score to improve."""

    cross_tenant_leaks: int = 0
    unauthorized_retrievals: int = 0
    prompt_injection_successes: int = 0
    privilege_escalations: int = 0
    tool_authorization_bypasses: int = 0

    @property
    def is_clean(self) -> bool:
        return (
            self.cross_tenant_leaks
            + self.unauthorized_retrievals
            + self.prompt_injection_successes
            + self.privilege_escalations
            + self.tool_authorization_bypasses
        ) == 0


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    passed: bool
    observed_behaviour: ExpectedBehaviour
    retrieved_chunk_ids: tuple[str, ...] = ()
    leaked_chunk_ids: tuple[str, ...] = ()
    failure_reason: str = ""


class Evaluator(Protocol):
    def run(self, cases: Sequence[GoldCase]) -> Sequence[CaseResult]: ...
