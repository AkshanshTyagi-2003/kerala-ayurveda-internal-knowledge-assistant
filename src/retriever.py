import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


class HybridRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        
        print(f"🔧 Initializing retriever with {len(chunks)} chunks")

        # -------- BM25 (lexical) --------
        self.tokenized_corpus = [
            chunk["text"].lower().split() for chunk in chunks
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
        print(f"✅ BM25 initialized")

        # -------- Semantic embeddings --------
        print(f"🔄 Loading sentence transformer model...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        corpus_texts = [chunk["text"] for chunk in chunks]
        print(f"🔄 Encoding {len(corpus_texts)} documents...")
        self.embeddings = self.model.encode(
            corpus_texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        
        print(f"✅ Embeddings created: shape {self.embeddings.shape}")

    def retrieve(
        self,
        query,
        top_k=5,
        bm25_weight=0.3,
        semantic_weight=0.7,
        semantic_threshold=0.15  # LOWERED from 0.20 - was still too strict
    ):
        """
        Hybrid retrieval: BM25 + semantic similarity.
        Returns chunks that pass the semantic threshold.
        """

        # BM25 scoring
        query_tokens = query.lower().split()
        bm25_scores = self.bm25.get_scores(query_tokens)

        # Semantic scoring
        query_embedding = self.model.encode(
            query,
            normalize_embeddings=True
        )
        semantic_scores = np.dot(self.embeddings, query_embedding)

        # Normalize BM25 to [0, 1]
        bm25_min = np.min(bm25_scores)
        bm25_max = np.max(bm25_scores)
        if bm25_max - bm25_min > 1e-8:
            bm25_norm = (bm25_scores - bm25_min) / (bm25_max - bm25_min)
        else:
            bm25_norm = np.zeros_like(bm25_scores)

        # Hybrid score (semantic dominates)
        hybrid_scores = (
            bm25_weight * bm25_norm +
            semantic_weight * semantic_scores
        )

        # Rank by hybrid score
        ranked_indices = np.argsort(hybrid_scores)[::-1]

        results = []

        for idx in ranked_indices[:top_k * 2]:  # Check more candidates
            # Apply semantic gate
            if semantic_scores[idx] < semantic_threshold:
                continue

            chunk = self.chunks[idx]
            results.append({
                "doc_id": chunk["doc_id"],
                "section_id": chunk["section_id"],
                "text": chunk["text"],
                "type": chunk["type"],
                "semantic_score": float(semantic_scores[idx]),
                "bm25_score": float(bm25_scores[idx]),
                "hybrid_score": float(hybrid_scores[idx])
            })

            if len(results) >= top_k:
                break

        # Debug output
        print(f"\n🔍 Query: {query}")
        print(f"📊 Found {len(results)} chunks passing threshold {semantic_threshold}")
        for i, r in enumerate(results[:3], 1):
            print(f"   {i}. {r['doc_id']} ({r['type']}) - semantic: {r['semantic_score']:.3f}")

        return results