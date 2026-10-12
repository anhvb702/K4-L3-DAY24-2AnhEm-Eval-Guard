from __future__ import annotations

"""Module 3: Reranking — Cross-encoder top-20 → top-3 + latency benchmark."""

import math
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RERANK_MODEL, RERANK_TOP_K


@dataclass
class RerankResult:
    text: str
    original_score: float
    rerank_score: float
    metadata: dict
    rank: int


class CrossEncoderReranker:
    def __init__(self, model_name: str = RERANK_MODEL):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        """Rerank documents: top-20 → top-k."""
        if not documents or not query or not query.strip() or top_k <= 0:
            return []

        pairs = [(query, document["text"]) for document in documents]
        predictions = self._load_model().predict(pairs)

        import numpy as np

        scores = np.asarray(predictions)
        if scores.ndim == 0 and len(documents) == 1:
            scores = scores.reshape(1)
        if scores.ndim != 1 or len(scores) != len(documents):
            raise ValueError(
                f"CrossEncoder returned {scores.size} scores for {len(documents)} documents"
            )

        try:
            numeric_scores = [float(score) for score in scores]
        except (TypeError, ValueError) as error:
            raise ValueError("CrossEncoder returned non-numeric scores") from error
        if not all(math.isfinite(score) for score in numeric_scores):
            raise ValueError("CrossEncoder returned scores that are not finite")

        ranked = sorted(
            zip(numeric_scores, documents),
            key=lambda item: item[0],
            reverse=True,
        )[:top_k]
        return [
            RerankResult(
                text=document["text"],
                original_score=float(document.get("score", 0.0)),
                rerank_score=score,
                metadata=dict(document.get("metadata") or {}),
                rank=rank,
            )
            for rank, (score, document) in enumerate(ranked)
        ]


class FlashrankReranker:
    """Optional alternative unavailable in this project; use CrossEncoderReranker."""
    def __init__(self):
        self._model = None

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        raise NotImplementedError(
            "FlashrankReranker is optional and unavailable; use CrossEncoderReranker"
        )


def benchmark_reranker(reranker, query: str, documents: list[dict], n_runs: int = 5) -> dict:
    """Measure warm reranking latency over n_runs, excluding model load time."""
    if isinstance(n_runs, bool) or not isinstance(n_runs, int) or n_runs <= 0:
        raise ValueError("n_runs must be a positive integer")

    load_model = getattr(reranker, "_load_model", None)
    if callable(load_model):
        load_model()

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        reranker.rerank(query, documents)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return {"avg_ms": sum(times) / len(times), "min_ms": min(times), "max_ms": max(times)}


if __name__ == "__main__":
    query = "Nhân viên được nghỉ phép bao nhiêu ngày?"
    docs = [
        {"text": "Nhân viên được nghỉ 12 ngày/năm.", "score": 0.8, "metadata": {}},
        {"text": "Mật khẩu thay đổi mỗi 90 ngày.", "score": 0.7, "metadata": {}},
        {"text": "Thời gian thử việc là 60 ngày.", "score": 0.75, "metadata": {}},
    ]
    reranker = CrossEncoderReranker()
    for r in reranker.rerank(query, docs):
        print(f"[{r.rank}] {r.rerank_score:.4f} | {r.text}")
