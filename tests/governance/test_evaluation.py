"""Runs the Acme ISD gold set end to end.

This is the test that would catch a regression in *behaviour* rather than in a
unit: it exercises authorization, retrieval, fusion, reranking, and the
corrective gate together, from a data file a district can edit without touching
Python.
"""

from pathlib import Path

import pytest

from inflexis.authz import PolicyEngine
from inflexis.contracts.identity import Role
from inflexis.evaluation import EvaluationHarness, load_gold_set
from inflexis.fixtures import ACME, build_two_tenant_index, principals
from inflexis.retrieval import (
    BM25Retriever,
    HeuristicReranker,
    HybridRetrievalPipeline,
    VectorRetriever,
)

REPO = Path(__file__).resolve().parents[2]
GOLD_SET = REPO / "governance/evaluation/acme-isd-gold-set.json"


@pytest.fixture
def report():
    index = build_two_tenant_index()
    engine = PolicyEngine(ACME)
    pipeline = HybridRetrievalPipeline(
        retrievers=[BM25Retriever(index), VectorRetriever(index)],
        reranker=HeuristicReranker(),
    )
    people = principals()
    by_role = {
        Role.PUBLIC: people["public"],
        Role.STUDENT: people["student"],
        Role.TEACHER: people["teacher"],
        Role.COUNSELOR: people["counselor"],
        Role.PRINCIPAL: people["principal"],
        Role.HR: people["hr"],
        Role.IT_ADMIN: people["it_admin"],
        Role.SUPERINTENDENT: people["superintendent"],
    }

    def run_query(principal, case):
        authorized = engine.authorize_retrieval(principal, case.query)
        # answer() runs the corrective loop to a terminal verdict, which is what
        # a real orchestrator does. Evaluating run() alone would score the
        # system on a provisional "try again" rather than on what a user sees.
        return pipeline.answer(authorized)

    harness = EvaluationHarness(run_query, by_role)
    return harness.run(load_gold_set(GOLD_SET))


def test_gold_set_has_refusal_and_leakage_cases():
    cases = load_gold_set(GOLD_SET)
    refusals = [c for c in cases if c.expected_behaviour.value == "refuse"]
    with_forbidden = [c for c in cases if c.forbidden_sources]
    assert len(refusals) >= 5, "a gold set without refusal cases measures only helpfulness"
    assert len(with_forbidden) >= 5, "a gold set needs explicit leakage cases"


def test_no_security_failures(report):
    assert report.security.is_clean, report.summary()
    assert not report.release_blocked


def test_no_case_leaks_a_forbidden_source(report):
    leaks = [r for r in report.results if r.leaked_chunk_ids]
    assert not leaks, [
        (r.case_id, r.leaked_chunk_ids) for r in leaks
    ]


def test_all_gold_cases_pass(report):
    failures = [
        (r.case_id, r.failure_reason) for r in report.results if not r.passed
    ]
    assert not failures, f"{report.summary()}\nfailures: {failures}"


def test_retrieval_metrics_are_reported(report):
    assert report.retrieval.recall_at_k > 0
    assert report.retrieval.mrr > 0
