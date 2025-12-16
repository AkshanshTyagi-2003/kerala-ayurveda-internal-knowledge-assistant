from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class HybridRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

        # Prepare corpus for BM25
        self.tokenized_corpus = [
            chunk["text"].lower().split() for chunk in chunks
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # Use TF-IDF instead of sentence-transformers (Python 3.13 compatible)
        self.vectorizer = TfidfVectorizer(
            max_features=384,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1
        )
        
        corpus_texts = [chunk["text"] for chunk in chunks]
        self.embeddings = self.vectorizer.fit_transform(corpus_texts).toarray()
        
        # Normalize embeddings
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        self.embeddings = self.embeddings / (norms + 1e-8)

    def retrieve(self, query, top_k=5, bm25_weight=0.5):
        query_tokens = query.lower().split()
        bm25_scores = self.bm25.get_scores(query_tokens)

        # Transform query using the same vectorizer
        query_embedding = self.vectorizer.transform([query]).toarray()[0]
        query_norm = np.linalg.norm(query_embedding)
        query_embedding = query_embedding / (query_norm + 1e-8)
        
        semantic_scores = np.dot(self.embeddings, query_embedding)

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