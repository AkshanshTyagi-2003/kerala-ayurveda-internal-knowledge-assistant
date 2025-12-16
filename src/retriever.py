from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import numpy as np


class HybridRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

        # Prepare corpus for BM25
        self.tokenized_corpus = [
            chunk["text"].lower().split() for chunk in chunks
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # ---- LAZY INIT FLAGS (ADDED, NOTHING REMOVED) ----
        self._embedder = None
        self._embeddings = None

    # ---- LAZY LOADER (ADDED) ----
    def _load_embeddings(self):
        if self._embedder is None:
            self._embedder = SentenceTransformer(
                "all-MiniLM-L6-v2",
                device="cpu"
            )

        if self._embeddings is None:
            self._embeddings = self._embedder.encode(
                [chunk["text"] for chunk in self.chunks],
                normalize_embeddings=True
            )

    def retrieve(self, query, top_k=5, bm25_weight=0.5):
        # ---- ENSURE EMBEDDINGS LOADED ONLY WHEN NEEDED ----
        self._load_embeddings()

        query_tokens = query.lower().split()
        bm25_scores = self.bm25.get_scores(query_tokens)

        query_embedding = self._embedder.encode(
            query, normalize_embeddings=True
        )
        semantic_scores = np.dot(self._embeddings, query_embedding)

        # Normalize scores
        bm25_norm = (bm25_scores - np.min(bm25_scores)) / (
            np.max(bm25_scores) - np.min(bm25_scores) + 1e-8
        )
        semantic_norm = (semantic_scores - np.min(semantic_scores)) / (
            np.max(semantic_scores) - np.min(semantic_scores) + 1e-8
        )

        hybrid_scores = (
            bm25_weight * bm25_norm +
            (1 - bm25_weight) * semantic_norm
        )

        ranked_indices = np.argsort(hybrid_scores)[::-1][:top_k]

        results = []
        for idx in ranked_indices:
            chunk = self.chunks[idx]
            results.append({
                "doc_id": chunk["doc_id"],
                "section_id": chunk["section_id"],
                "text": chunk["text"],
                "type": chunk["type"]
            })

        return results
