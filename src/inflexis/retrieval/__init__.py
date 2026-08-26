"""Plane 4: adaptive retrieval.

Hybrid retrieval (BM25 + vector -> RRF -> rerank) is the default strategy for
K-12 district knowledge; see ADR-002 for why.
"""

from .bm25 import BM25Retriever
from .vector import VectorRetriever
from .fusion import ReciprocalRankFusion
from .rerank import HeuristicReranker, ProviderReranker
from .corrective import CorrectiveChecker
from .pipeline import HybridRetrievalPipeline

__all__ = [
    "BM25Retriever",
    "VectorRetriever",
    "ReciprocalRankFusion",
    "HeuristicReranker",
    "ProviderReranker",
    "CorrectiveChecker",
    "HybridRetrievalPipeline",
]
