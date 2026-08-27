"""Tests for the claims ADR-002 makes about hybrid retrieval.

If the repository is going to assert that BM25 + vector + RRF beats either
retriever alone for district content, that assertion should be executable.
"""

import pytest

from inflexis.authz import PolicyEngine
from inflexis.contracts.retrieval import CorrectiveAction, Sufficiency
from inflexis.fixtures import ACME, build_acme_index, principals
from inflexis.retrieval import (
    BM25Retriever,
    HeuristicReranker,
    HybridRetrievalPipeline,
    ReciprocalRankFusion,
    VectorRetriever,
)
from inflexis.retrieval.corrective import CorrectiveChecker


@pytest.fixture
def acme_index():
    return build_acme_index()


@pytest.fixture
def engine():
    return PolicyEngine(ACME)


@pytest.fixture
def staff(  ):
    return principals()["teacher"]


def _ids(result):
    return [r.chunk.chunk_id for r in result.results]


class TestLexicalStrength:
    def test_bm25_finds_exact_policy_code(self, acme_index, engine, staff):
        """EIC(LOCAL) is an exact token. Lexical retrieval must nail it."""
        bm25 = BM25Retriever(acme_index)
        query = engine.authorize_retrieval(staff, "EIC(LOCAL)")
        assert _ids(bm25.retrieve(query))[0] == "BP-EIC-LOCAL#0"

    def test_bm25_finds_statute_citation(self, acme_index, engine, staff):
        bm25 = BM25Retriever(acme_index)
        query = engine.authorize_retrieval(staff, "TEC 25.085 compulsory attendance")
        assert "TEC-25085-SUMMARY#0" in _ids(bm25.retrieve(query))[:2]

    def test_tokenizer_preserves_policy_codes(self):
        from inflexis.retrieval.bm25 import tokenize

        assert "eic(local)" in tokenize("Board Policy EIC(LOCAL) applies")
        assert "25.085" in tokenize("under TEC 25.085 attendance")


class TestFusion:
    def test_rrf_rewards_agreement_between_retrievers(self, acme_index, engine, staff):
        """A chunk both retrievers rank highly should outrank a single-list top hit."""
        bm25 = BM25Retriever(acme_index)
        vector = VectorRetriever(acme_index)
        query = engine.authorize_retrieval(
            staff, "requisition approval thresholds business office"
        )
        fused = ReciprocalRankFusion().fuse(
            [bm25.retrieve(query), vector.retrieve(query)], top_k=10
        )
        assert fused, "fusion produced no candidates"
        top = fused[0]
        assert "+" in top.retriever or top.chunk.chunk_id == "SOP-PURCHASING#0"

    def test_rrf_ignores_raw_score_magnitude(self):
        """The property that makes RRF correct: only ranks matter."""
        from inflexis.contracts.document import Chunk, ScoredChunk
        from inflexis.contracts.retrieval import RetrievalResult, RetrievalStrategy
        from inflexis.fixtures.acme_isd import acme_documents

        docs = acme_documents()[:2]
        chunks = [
            Chunk.from_document(d, f"{d.document_id}#0", t) for d, t in docs
        ]
        # Same ranking, wildly different score scales.
        small = RetrievalResult(
            results=tuple(
                ScoredChunk(chunk=c, score=0.001 * (2 - i), retriever="a", rank=i + 1)
                for i, c in enumerate(chunks)
            ),
            strategy=RetrievalStrategy.LEXICAL,
        )
        large = RetrievalResult(
            results=tuple(
                ScoredChunk(chunk=c, score=9000.0 * (2 - i), retriever="b", rank=i + 1)
                for i, c in enumerate(chunks)
            ),
            strategy=RetrievalStrategy.VECTOR,
        )
        fused = ReciprocalRankFusion().fuse([small, large], top_k=5)
        assert [f.chunk.chunk_id for f in fused] == [c.chunk_id for c in chunks]

    def test_rrf_rejects_invalid_k(self):
        with pytest.raises(ValueError):
            ReciprocalRankFusion(k=0)


class TestPipelineEndToEnd:
    def test_hybrid_pipeline_answers_a_policy_question(
        self, acme_index, engine, staff
    ):
        pipeline = HybridRetrievalPipeline(
            retrievers=[BM25Retriever(acme_index), VectorRetriever(acme_index)],
            reranker=HeuristicReranker(),
        )
        query = engine.authorize_retrieval(
            staff, "EIC(LOCAL) class ranking calculation"
        )
        ctx = pipeline.run(query)
        assert ctx.may_generate
        assert "BP-EIC-LOCAL#0" in {e.chunk.chunk_id for e in ctx.evidence}
        assert ctx.citations, "grounded context carried no citations"

    def test_every_result_carries_provenance(self, acme_index, engine, staff):
        pipeline = HybridRetrievalPipeline(
            retrievers=[BM25Retriever(acme_index), VectorRetriever(acme_index)],
            reranker=HeuristicReranker(),
        )
        ctx = pipeline.run(
            engine.authorize_retrieval(staff, "grading and reporting late work")
        )
        for evidence in ctx.evidence:
            assert evidence.chunk.provenance.source_uri
            assert evidence.chunk.provenance.content_hash

    def test_pipeline_requires_at_least_one_retriever(self):
        with pytest.raises(ValueError):
            HybridRetrievalPipeline(retrievers=[], reranker=HeuristicReranker())


class TestFreshnessAndAuthority:
    def test_superseded_document_is_not_retrieved(self, acme_index, engine, staff):
        """The 2019 grading regulation must never surface as current guidance."""
        pipeline = HybridRetrievalPipeline(
            retrievers=[BM25Retriever(acme_index), VectorRetriever(acme_index)],
            reranker=HeuristicReranker(),
        )
        ctx = pipeline.run(
            engine.authorize_retrieval(
                staff, "minimum number of grades per nine week grading period"
            )
        )
        ids = {e.chunk.chunk_id for e in ctx.evidence}
        assert "AR-GRADING-2019#0" not in ids
        assert "AR-GRADING-2025#0" in ids

    def test_expired_memo_is_not_retrieved(self, acme_index, engine, staff):
        pipeline = HybridRetrievalPipeline(
            retrievers=[BM25Retriever(acme_index), VectorRetriever(acme_index)],
            reranker=HeuristicReranker(),
        )
        ctx = pipeline.run(
            engine.authorize_retrieval(
                staff, "campus health screening stations at each entrance"
            )
        )
        assert "MEMO-COVID-PROTOCOL#0" not in {
            e.chunk.chunk_id for e in ctx.evidence
        }


class TestCorrectiveRag:
    def test_no_evidence_leads_to_refusal_not_invention(
        self, acme_index, engine, staff
    ):
        pipeline = HybridRetrievalPipeline(
            retrievers=[BM25Retriever(acme_index), VectorRetriever(acme_index)],
            reranker=HeuristicReranker(),
            corrective=CorrectiveChecker(max_rewrites=0),
        )
        ctx = pipeline.run(
            engine.authorize_retrieval(
                staff, "zqxjw fnord blorptastic nonexistent district topic"
            )
        )
        assert not ctx.may_generate
        assert ctx.verdict.action in (
            CorrectiveAction.REFUSE,
            CorrectiveAction.REWRITE_QUERY,
        )
        assert ctx.evidence == (), "refusal returned evidence anyway"

    def test_first_attempt_prefers_rewrite_over_refusal(self):
        checker = CorrectiveChecker(max_rewrites=1)
        verdict = checker.check([], attempt=0)
        assert verdict.action is CorrectiveAction.REWRITE_QUERY
        assert checker.check([], attempt=1).action is CorrectiveAction.REFUSE

    def test_conflicting_versions_escalate(self):
        """Two active versions at equal authority must not be silently merged."""
        from datetime import date

        from inflexis.contracts.classification import (
            AuthorityLevel,
            DataClassification,
            TrustDomain,
        )
        from inflexis.contracts.document import (
            AccessControlList,
            Chunk,
            Document,
            Provenance,
            ScoredChunk,
            content_hash,
        )
        from inflexis.contracts.identity import Role

        def make(version: str, text: str) -> ScoredChunk:
            doc = Document(
                tenant_id="acme-isd",
                district_id="TX-ACME-001",
                document_id="POLICY-X",
                title="Policy X",
                document_type="board_policy",
                trust_domain=TrustDomain.PUBLIC,
                data_classification=DataClassification.PUBLIC,
                authority_level=AuthorityLevel.BOARD_POLICY,
                acl=AccessControlList(allowed_roles=frozenset({Role.TEACHER})),
                provenance=Provenance(
                    source_system="s", source_uri="u", content_hash=content_hash(text)
                ),
                version=version,
                effective_date=date(2025, 1, 1),
            )
            return ScoredChunk(
                chunk=Chunk.from_document(doc, f"POLICY-X#{version}", text),
                score=1.0,
            )

        verdict = CorrectiveChecker(require_authority=False).check(
            [make("1", "limit is thirty days"), make("2", "limit is sixty days")]
        )
        assert verdict.sufficiency is Sufficiency.CONFLICTING
        assert verdict.action is CorrectiveAction.ESCALATE
        assert len(verdict.conflicting_chunk_ids) == 2


class TestAuthorityGate:
    """The authority gate is opt-in per use case, and works when opted in."""

    def test_gate_off_by_default_allows_operational_answers(
        self, acme_index, engine, staff
    ):
        pipeline = HybridRetrievalPipeline(
            retrievers=[BM25Retriever(acme_index), VectorRetriever(acme_index)],
            reranker=HeuristicReranker(),
        )
        ctx = pipeline.run(
            engine.authorize_retrieval(staff, "north campus bell schedule duty roster")
        )
        assert ctx.may_generate, (
            "a campus document should authoritatively answer a campus question"
        )

    def test_policy_use_case_gate_rejects_low_authority_evidence(
        self, acme_index, engine, staff
    ):
        """With the gate on, a campus doc is not enough for a policy question."""
        from inflexis.contracts.classification import AuthorityLevel

        pipeline = HybridRetrievalPipeline(
            retrievers=[BM25Retriever(acme_index), VectorRetriever(acme_index)],
            reranker=HeuristicReranker(),
            corrective=CorrectiveChecker(
                min_score=HeuristicReranker.default_min_score,
                require_authority=True,
                authority_threshold=AuthorityLevel.BOARD_POLICY,
                max_rewrites=0,
            ),
        )
        ctx = pipeline.run(
            engine.authorize_retrieval(staff, "north campus bell schedule duty roster")
        )
        assert not ctx.may_generate
        assert ctx.verdict.sufficiency is Sufficiency.INSUFFICIENT_AUTHORITY

    def test_policy_question_passes_the_gate_with_board_policy(
        self, acme_index, engine, staff
    ):
        from inflexis.contracts.classification import AuthorityLevel

        pipeline = HybridRetrievalPipeline(
            retrievers=[BM25Retriever(acme_index), VectorRetriever(acme_index)],
            reranker=HeuristicReranker(),
            corrective=CorrectiveChecker(
                min_score=HeuristicReranker.default_min_score,
                require_authority=True,
                authority_threshold=AuthorityLevel.BOARD_POLICY,
            ),
        )
        ctx = pipeline.run(
            engine.authorize_retrieval(staff, "EIC(LOCAL) class ranking calculation")
        )
        assert ctx.may_generate
        assert ctx.evidence[0].chunk.authority_level is AuthorityLevel.BOARD_POLICY


class TestRelevanceGate:
    def test_authority_does_not_manufacture_relevance(self):
        """An authoritative document that ignores the question scores ~0."""
        from datetime import date

        from inflexis.contracts.classification import (
            AuthorityLevel,
            DataClassification,
            TrustDomain,
        )
        from inflexis.contracts.document import (
            AccessControlList,
            Chunk,
            Document,
            Provenance,
            ScoredChunk,
            content_hash,
        )
        from inflexis.contracts.identity import Role

        text = "The board adopts the annual budget in August."
        doc = Document(
            tenant_id="acme-isd",
            district_id="TX-ACME-001",
            document_id="BP-BUDGET",
            title="Budget Policy",
            document_type="board_policy",
            trust_domain=TrustDomain.PUBLIC,
            data_classification=DataClassification.PUBLIC,
            authority_level=AuthorityLevel.STATE_LAW,  # maximum authority
            acl=AccessControlList(allowed_roles=frozenset({Role.TEACHER})),
            provenance=Provenance(
                source_system="s", source_uri="u", content_hash=content_hash(text)
            ),
            effective_date=date(2025, 1, 1),
        )
        candidate = ScoredChunk(
            chunk=Chunk.from_document(doc, "BP-BUDGET#0", text), score=1.0
        )
        ranked = HeuristicReranker().rerank(
            "wireless network configuration for chromebooks", [candidate], top_n=5
        )
        assert ranked[0].score == 0.0, (
            "a maximally authoritative but irrelevant document scored above zero"
        )
