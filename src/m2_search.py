from __future__ import annotations

"""Module 2: Hybrid Search — BM25 (Vietnamese) + Dense + RRF."""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    BM25_TOP_K,
    COLLECTION_NAME,
    DENSE_TOP_K,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    HYBRID_TOP_K,
    QDRANT_HOST,
    QDRANT_PORT,
)


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict
    method: str  # "bm25", "dense", "hybrid"


def segment_vietnamese(text: str) -> str:
    """Segment Vietnamese text into words."""
    if not text or not text.strip():
        return ""

    from underthesea import word_tokenize

    segmented = word_tokenize(text.lower(), format="text")
    return segmented.replace("_", " ").lower()


class BM25Search:
    def __init__(self):
        self.corpus_tokens = []
        self.documents = []
        self.bm25 = None

    def index(self, chunks: list[dict]) -> None:
        """Build BM25 index from chunks."""
        from rank_bm25 import BM25Okapi

        self.documents = []
        self.corpus_tokens = []
        self.bm25 = None

        for chunk in chunks:
            text = chunk.get("text", "")
            if not text or not text.strip():
                continue
            tokens = segment_vietnamese(text).split()
            if tokens:
                self.documents.append({
                    "text": text,
                    "metadata": dict(chunk.get("metadata") or {}),
                })
                self.corpus_tokens.append(tokens)

        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, top_k: int = BM25_TOP_K) -> list[SearchResult]:
        """Search using BM25."""
        if self.bm25 is None or top_k <= 0 or not query or not query.strip():
            return []

        tokens = segment_vietnamese(query).split()
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)
        ranked_indices = sorted(
            (index for index, score in enumerate(scores) if score > 0),
            key=lambda index: scores[index],
            reverse=True,
        )[:top_k]
        return [
            SearchResult(
                text=self.documents[index]["text"],
                score=float(scores[index]),
                metadata=dict(self.documents[index]["metadata"]),
                method="bm25",
            )
            for index in ranked_indices
        ]


class DenseSearch:
    def __init__(self):
        from qdrant_client import QdrantClient

        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30)
        self.client.get_collections()
        self.backend = "server"
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer(EMBEDDING_MODEL)
        return self._encoder

    def index(self, chunks: list[dict], collection: str = COLLECTION_NAME) -> None:
        """Index chunks into Qdrant."""
        import numpy as np
        from qdrant_client.models import Distance, PointStruct, VectorParams

        if chunks:
            texts = [chunk["text"] for chunk in chunks]
            vectors = np.asarray(self._get_encoder().encode(texts, show_progress_bar=True))
            if vectors.ndim != 2 or vectors.shape != (len(chunks), EMBEDDING_DIM):
                actual = vectors.shape[-1] if vectors.ndim else 0
                raise ValueError(
                    f"Embedding dimension mismatch: expected {EMBEDDING_DIM}, got {actual}"
                )
        else:
            vectors = []

        if self.client.collection_exists(collection):
            self.client.delete_collection(collection)
        self.client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )

        if not chunks:
            return

        points = [
            PointStruct(
                id=index,
                vector=vector.tolist(),
                payload={**(chunk.get("metadata") or {}), "text": chunk["text"]},
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        self.client.upsert(collection_name=collection, points=points, wait=True)

    def search(self, query: str, top_k: int = DENSE_TOP_K, collection: str = COLLECTION_NAME) -> list[SearchResult]:
        """Search using dense vectors."""
        if top_k <= 0 or not query or not query.strip():
            return []
        if not self.client.collection_exists(collection):
            return []

        import numpy as np

        query_vector = np.asarray(self._get_encoder().encode(query.strip()))
        if query_vector.ndim != 1 or query_vector.shape[0] != EMBEDDING_DIM:
            actual = query_vector.shape[-1] if query_vector.ndim else 0
            raise ValueError(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIM}, got {actual}"
            )

        response = self.client.search(
            collection_name=collection,
            query_vector=query_vector.tolist(),
            limit=top_k,
            with_payload=True,
        )
        return [
            SearchResult(
                text=(point.payload or {}).get("text", ""),
                score=float(point.score),
                metadata=dict(point.payload or {}),
                method="dense",
            )
            for point in response
        ]


def reciprocal_rank_fusion(results_list: list[list[SearchResult]], k: int = 60,
                           top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
    """Merge ranked lists using RRF: score(d) = Σ 1/(k + rank + 1)."""
    if k <= 0:
        raise ValueError("k must be a positive integer")
    if top_k <= 0:
        return []

    fused = {}
    for results in results_list:
        for rank, result in enumerate(results):
            if result.text not in fused:
                fused[result.text] = {"score": 0.0, "result": result}
            fused[result.text]["score"] += 1.0 / (k + rank + 1)

    ranked = sorted(fused.values(), key=lambda item: item["score"], reverse=True)[:top_k]
    return [
        SearchResult(
            text=item["result"].text,
            score=item["score"],
            metadata=item["result"].metadata,
            method="hybrid",
        )
        for item in ranked
    ]


class HybridSearch:
    """Combines BM25 + Dense + RRF. (Đã implement sẵn — dùng classes ở trên)"""
    def __init__(self):
        self.bm25 = BM25Search()
        self.dense = DenseSearch()

    def index(self, chunks: list[dict], collection: str = COLLECTION_NAME) -> None:
        self.bm25.index(chunks)
        self.dense.index(chunks, collection=collection)

    def search(self, query: str, top_k: int = HYBRID_TOP_K,
               collection: str = COLLECTION_NAME) -> list[SearchResult]:
        if top_k <= 0 or not query or not query.strip():
            return []
        bm25_results = self.bm25.search(query, top_k=BM25_TOP_K)
        dense_results = self.dense.search(query, top_k=DENSE_TOP_K, collection=collection)
        return reciprocal_rank_fusion([bm25_results, dense_results], top_k=top_k)


if __name__ == "__main__":
    print("Original:  Nhân viên được nghỉ phép năm")
    print(f"Segmented: {segment_vietnamese('Nhân viên được nghỉ phép năm')}")
