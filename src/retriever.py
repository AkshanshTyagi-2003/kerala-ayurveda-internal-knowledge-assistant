from rank_bm25 import BM25Okapi


class HybridRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

        # Prepare corpus for BM25
        self.tokenized_corpus = [
            chunk["text"].lower().split() for chunk in chunks
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def retrieve(self, query, top_k=5):
        query_tokens = query.lower().split()
        scores = self.bm25.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

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
