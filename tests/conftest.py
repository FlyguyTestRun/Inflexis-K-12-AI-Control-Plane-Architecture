"""Shared fixtures. Adds ``src`` to the path so tests run without install."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inflexis.audit import InMemoryAuditSink  # noqa: E402
from inflexis.authz import PolicyEngine  # noqa: E402
from inflexis.fixtures import (  # noqa: E402
    ACME,
    BRAVO,
    build_two_tenant_index,
    principals,
)
from inflexis.retrieval import (  # noqa: E402
    BM25Retriever,
    HeuristicReranker,
    HybridRetrievalPipeline,
    VectorRetriever,
)


@pytest.fixture
def index():
    """Both districts co-located in one index -- the realistic deployment."""
    return build_two_tenant_index()


@pytest.fixture
def people():
    return principals()


@pytest.fixture
def acme_engine():
    return PolicyEngine(ACME)


@pytest.fixture
def bravo_engine():
    return PolicyEngine(BRAVO)


@pytest.fixture
def audit():
    return InMemoryAuditSink()


@pytest.fixture
def pipeline(index, audit):
    return HybridRetrievalPipeline(
        retrievers=[BM25Retriever(index), VectorRetriever(index)],
        reranker=HeuristicReranker(),
        audit_sink=audit,
    )


def retrieve_text(pipeline, engine, principal, query, **kwargs):
    """Run a full authorized retrieval and return the grounded context."""
    authorized = engine.authorize_retrieval(principal, query, **kwargs)
    return pipeline.run(authorized)
