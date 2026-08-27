"""Tests for informativeness-weighted relevance and the corrective loop.

Both mechanisms exist because the naive versions produced confident answers to
questions the corpus does not address. These tests pin the fixes.
"""

import pytest

from inflexis.authz import PolicyEngine
from inflexis.contracts.retrieval import CorrectiveAction
from inflexis.fixtures import ACME, build_two_tenant_index, principals
from inflexis.retrieval import (
    BM25Retriever,
    HeuristicReranker,
    HybridRetrievalPipeline,
    VectorRetriever,
)


@pytest.fixture
def index():
    return build_two_tenant_index()


@pytest.fixture
def engine():
    return PolicyEngine(ACME)


@pytest.fixture
def pipeline(index):
    return HybridRetrievalPipeline(
        retrievers=[BM25Retriever(index), VectorRetriever(index)],
        reranker=HeuristicReranker(),
    )


class TestCorpusStatistics:
    def test_rare_terms_outweigh_common_terms(self, index):
        stats = index.statistics("acme-isd")
        assert stats.weight("interplanetary") > stats.weight("district")
        assert stats.weight("eic(local)") > stats.weight("the")

    def test_statistics_are_tenant_scoped(self, index):
        """Cross-tenant statistics would be a ranking side channel."""
        acme = index.statistics("acme-isd")
        bravo = index.statistics("bravo-isd")
        assert acme.n_docs != bravo.n_docs
        # A term unique to Bravo must not appear in Acme's statistics.
        assert "bravo" not in acme.document_frequency

    def test_unknown_tenant_yields_empty_statistics(self, index):
        assert index.statistics("nonexistent-isd").n_docs == 0


class TestInformativenessGate:
    def test_stopword_only_overlap_does_not_clear_the_gate(
        self, pipeline, engine
    ):
        """The regression this weighting exists to prevent.

        "district" and "policy" match many documents; "interplanetary" matches
        none. Unweighted coverage rated this a confident hit against unrelated
        board policy.
        """
        ctx = pipeline.answer(
            engine.authorize_retrieval(
                principals()["teacher"],
                "What is the district policy on interplanetary field trips?",
            )
        )
        assert not ctx.may_generate
        assert ctx.evidence == ()

    def test_unauthorized_topic_yields_refusal_not_a_near_miss(
        self, pipeline, engine
    ):
        ctx = pipeline.answer(
            engine.authorize_retrieval(
                principals()["public"],
                "What are the district requisition approval thresholds?",
            )
        )
        assert not ctx.may_generate

    def test_informative_query_still_answers(self, pipeline, engine):
        ctx = pipeline.answer(
            engine.authorize_retrieval(
                principals()["teacher"], "What does EIC(LOCAL) say about class ranking?"
            )
        )
        assert ctx.may_generate
        assert ctx.evidence[0].chunk.chunk_id == "BP-EIC-LOCAL#0"


class TestCorrectiveLoop:
    def test_loop_reaches_a_terminal_verdict_without_a_rewriter(
        self, pipeline, engine
    ):
        """Never hand the caller a provisional 'try again' it cannot act on."""
        ctx = pipeline.answer(
            engine.authorize_retrieval(
                principals()["teacher"], "zzzz qqqq nonexistent unmatched topic"
            )
        )
        assert ctx.verdict.action not in (
            CorrectiveAction.REWRITE_QUERY,
            CorrectiveAction.BROADEN_SOURCES,
        )
        assert ctx.verdict.action is CorrectiveAction.REFUSE

    def test_rewrite_is_reauthorized_rather_than_reusing_the_filter(
        self, pipeline, engine
    ):
        """A rewritten query must go back through the policy decision point."""
        teacher = principals()["teacher"]
        seen: list[str] = []

        def reauthorize(text: str):
            seen.append(text)
            return engine.authorize_retrieval(teacher, text)

        def rewrite(text: str, attempt: int) -> str:
            return "EIC(LOCAL) class ranking"

        ctx = pipeline.answer(
            engine.authorize_retrieval(teacher, "zzzz qqqq unmatched"),
            reauthorize=reauthorize,
            rewrite=rewrite,
        )
        assert seen == ["EIC(LOCAL) class ranking"], (
            "rewritten query did not pass back through the policy decision point"
        )
        assert ctx.may_generate

    def test_loop_respects_the_rewrite_budget(self, pipeline, engine):
        teacher = principals()["teacher"]
        attempts: list[int] = []

        def rewrite(text: str, attempt: int) -> str:
            attempts.append(attempt)
            return "still nothing zzzz qqqq"

        pipeline.answer(
            engine.authorize_retrieval(teacher, "zzzz qqqq unmatched"),
            reauthorize=lambda t: engine.authorize_retrieval(teacher, t),
            rewrite=rewrite,
        )
        assert len(attempts) <= 1, f"exceeded rewrite budget: {attempts}"
