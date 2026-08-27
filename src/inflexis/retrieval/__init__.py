"""Plane 4: adaptive retrieval.

Hybrid retrieval (BM25 + vector -> RRF -> rerank) is the default strategy for
K-12 district knowledge; see ADR-002 for why.
"""

from .bm25 import BM25Retriever
from .corrective import CorrectiveChecker
from .fusion import ReciprocalRankFusion
from .pipeline import HybridRetrievalPipeline
from .rerank import HeuristicReranker, ProviderReranker
from .vector import VectorRetriever

__all__ = [
    "BM25Retriever",
    "VectorRetriever",
    "ReciprocalRankFusion",
    "HeuristicReranker",
    "ProviderReranker",
    "CorrectiveChecker",
    "HybridRetrievalPipeline",
]
