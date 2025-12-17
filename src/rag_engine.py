from src.loader import load_all_documents
from src.chunking import chunk_markdown_document, chunk_csv_rows
from src.retriever import HybridRetriever
import re


class KeralaAyurvedaRAG:
    def __init__(self):
        md_docs, csv_docs = load_all_documents()

        chunks = []
        for doc in md_docs:
            chunks.extend(chunk_markdown_document(doc))
        chunks.extend(chunk_csv_rows(csv_docs))

        self.retriever = HybridRetriever(chunks)

    # ----------------- SAFETY -----------------

    def _hard_block(self, query: str) -> bool:
        """Block medically unsafe queries."""
        q = query.lower()
        return any(word in q for word in [
            "cure", "permanent", "permanently", "diagnose",
            "dosage", "how many", "per day"
        ])

    # ----------------- AGGRESSIVE NOISE FILTERING -----------------

    def _is_editorial_or_metadata(self, line: str) -> bool:
        """
        Check if a line is editorial instruction or metadata (NOT content).
        Returns True if line should be SKIPPED.
        """
        lower = line.lower()
        
        # Editorial instruction markers
        editorial = [
            'keywords:', 'tendencies:', 'content hints:', 'emphasise',
            'mention', 'avoid', 'use phrases like', 'give examples like',
            'never hard-code', 'agents should', 'preferred phrasing:',
            'example boilerplate:', 'phrases that sound', 'phrases that do not',
            'internal tags:', 'related products:', 'see also:',
            'category:', 'format:', 'product name:', 'key herb:', 'basic info',
            'claims like', 'avoid words like', 'overpromising'
        ]
        
        if any(marker in lower for marker in editorial):
            return True
        
        # Lines that start with instruction verbs
        if lower.startswith(('emphasise', 'mention', 'avoid', 'use phrases', 
                            'give examples', 'never', 'always', 'claims like')):
            return True
        
        # Quote examples (editorial examples, not actual content)
        if '"' in line:
            return True
        
        # Example phrases
        if lower.startswith(('for example:', 'e.g.', 'such as:')):
            return True
        
        return False

    def _extract_content_lines(self, text: str) -> list[str]:
        """Extract only actual content lines (prose about Ayurveda)."""
        lines = text.splitlines()
        content = []
        in_imbalance_section = False
        in_tendencies_section = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty
            if not line:
                continue
            
            # Skip headers
            if line.startswith('#'):
                continue
            
            # Skip metadata markers
            if line.startswith(('---', '___', '>', '_')):
                continue
            
            # Track section context
            lower = line.lower()
            if 'imbalance may show as:' in lower:
                in_imbalance_section = True
                continue  # Skip the label itself
            elif 'common tendencies' in lower and ':' in line:
                in_tendencies_section = True
                continue  # Skip the label itself
            elif lower.startswith('content hints:'):
                in_imbalance_section = False
                in_tendencies_section = False
                continue
            
            # Skip editorial (but NOT content bullets)
            if not (in_imbalance_section or in_tendencies_section):
                if self._is_editorial_or_metadata(line):
                    continue
            
            # Handle bullets
            if line.startswith(('-', '*', '•')):
                content_text = re.sub(r'^[\-\*•]\s+', '', line).strip()
                
                # In symptom/tendency sections, keep all bullets
                if in_imbalance_section or in_tendencies_section:
                    if len(content_text) >= 15:
                        content.append(content_text)
                    continue
                
                # Outside those sections, skip short/label bullets
                if len(content_text) >= 25 and ':' not in content_text[:15]:
                    content.append(content_text)
                continue
            
            # Reset section flags when we hit a new section
            if line and not line.startswith(('-', '*', '•')):
                if 'content hints' not in lower:
                    in_imbalance_section = False
                    in_tendencies_section = False
            
            # Keep substantial prose lines
            if len(line) >= 25:
                content.append(line)
        
        return content

    def _build_prose(self, lines: list[str]) -> str:
        """Convert content lines to continuous prose."""
        # Join lines
        text = ' '.join(lines)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove markdown formatting
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)      # Italic
        text = re.sub(r'_(.+?)_', r'\1', text)        # Underscore
        return text

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split prose into quality sentences."""
        # For symptom lists, treat each item as a sentence
        # Split on sentence boundaries OR newlines (for list items)
        raw_sentences = re.split(r'(?<=[.!?])\s+|\n', text)
        
        sentences = []
        for sent in raw_sentences:
            sent = sent.strip()
            
            # Must have some substance
            if len(sent) < 15 or len(sent.split()) < 3:
                continue
            
            # Skip pure section labels
            if sent.endswith(':') and len(sent) < 40:
                continue
            
            # Final check: skip if contains editorial markers (but allow symptom descriptions)
            if self._is_editorial_or_metadata(sent):
                continue
            
            sentences.append(sent)
        
        return sentences

    def _score_sentence(self, sentence: str, query: str, keywords: set) -> float:
        """Score sentence relevance to query."""
        s = sentence.lower()
        q = query.lower()
        
        score = 0.0
        
        # Keyword matches
        matches = sum(1 for kw in keywords if kw in s)
        score += matches * 1.5
        
        # What is / definitional questions
        if 'what is' in q or 'what does' in q or 'according to' in q:
            definitional = [
                'is a traditional', 'is an ancient', 'system of', 'originated',
                'focuses on', 'refers to', 'means'
            ]
            if any(marker in s for marker in definitional):
                score += 5.0
        
        # Dosha description questions
        if any(w in q for w in ['vata', 'pitta', 'kapha', 'dosha', 'mean by']):
            dosha_markers = [
                'groups functions', 'principles called', 'doshas',
                'associated with', 'vata', 'pitta', 'kapha'
            ]
            if any(marker in s for marker in dosha_markers):
                score += 4.0
        
        # Imbalance questions
        if 'imbalance' in q or 'signs' in q or 'symptoms' in q:
            symptom_markers = [
                'restlessness', 'worry', 'scattered', 'irregular',
                'irritability', 'impatience', 'lethargy', 'stuck',
                'may show as', 'tendency to'
            ]
            if any(marker in s for marker in symptom_markers):
                score += 4.0
        
        # Traditional use / product questions
        if 'traditionally' in q or 'used for' in q:
            usage_markers = [
                'traditionally used', 'support', 'helps', 'maintain',
                'promote', 'used to', 'ability to adapt'
            ]
            if any(marker in s for marker in usage_markers):
                score += 4.0
        
        return score

    def _extract_answer(self, chunk_text: str, query: str) -> list[str]:
        """Extract best answer sentences from chunk."""
        # Get content lines
        lines = self._extract_content_lines(chunk_text)
        
        if not lines:
            return []
        
        # Build prose
        prose = self._build_prose(lines)
        
        if not prose:
            return []
        
        # Split into sentences
        sentences = self._split_into_sentences(prose)
        
        if not sentences:
            return []
        
        # Get query keywords
        stop_words = {
            'what', 'is', 'are', 'the', 'a', 'an', 'how', 'does', 'do',
            'can', 'i', 'in', 'for', 'to', 'and', 'or', 'by', 'according',
            'mean', 'means', 'kerala', 'ayurveda', 'described', 'when',
            'out', 'of', 'common', 'traditionally', 'used'
        }
        keywords = set(query.lower().split()) - stop_words
        
        # Score sentences
        scored = []
        for sent in sentences:
            score = self._score_sentence(sent, query, keywords)
            if score > 0:
                scored.append((score, sent))
        
        # Sort by score
        scored.sort(reverse=True, key=lambda x: x[0])
        
        # Return top 2 per chunk
        return [sent for _, sent in scored[:2]]

    # ----------------- CHUNK SELECTION -----------------

    def _select_chunks(self, query: str, chunks: list[dict]) -> list[dict]:
        """Select best chunks for query."""
        q = query.lower()
        selected = []
        
        # Product-specific
        for name in ['ashwagandha', 'triphala', 'brahmi']:
            if name in q:
                for c in chunks:
                    if name in c["doc_id"].lower():
                        selected.append(c)
                if selected:
                    return selected[:2]
        
        # Imbalance questions - be specific about which dosha
        if 'imbalance' in q or 'signs' in q or 'symptoms' in q:
            target_dosha = None
            if 'vata' in q:
                target_dosha = 'vata'
            elif 'pitta' in q:
                target_dosha = 'pitta'
            elif 'kapha' in q:
                target_dosha = 'kapha'
            
            if target_dosha:
                # Get ONLY the chunk for that specific dosha
                for c in chunks:
                    if 'dosha_guide' in c["doc_id"].lower():
                        # Check if this chunk is about the target dosha
                        if target_dosha in c["text"].lower()[:100]:  # Check start of chunk
                            selected.append(c)
                            return selected[:1]  # Return only 1 chunk for specific dosha
        
        # Dosha questions (general)
        if any(w in q for w in ['vata', 'pitta', 'kapha', 'dosha', 'mean by']):
            # First try ayurveda_foundations for "what does mean by"
            if 'mean by' in q or 'what does ayurveda' in q:
                for c in chunks:
                    if 'ayurveda_foundations' in c["doc_id"].lower():
                        selected.append(c)
                if selected:
                    return selected[:2]
            
            # Then dosha guide for specifics
            for c in chunks:
                if 'dosha_guide' in c["doc_id"].lower():
                    selected.append(c)
            if selected:
                return selected[:2]
        
        # "What is Ayurveda" - prioritize foundations
        if 'what is ayurveda' in q or 'according to kerala' in q:
            for c in chunks:
                if 'ayurveda_foundations' in c["doc_id"].lower():
                    selected.append(c)
            if selected:
                return selected[:2]
        
        # Fallback
        return chunks[:2]

    # ----------------- ANSWER SYNTHESIS -----------------

    def _synthesise_answer(self, query: str, chunks: list[dict]) -> tuple[str, list[dict]]:
        """Create final answer from chunks."""
        
        if self._hard_block(query):
            return "This information is not available in our internal corpus.", []
        
        selected = self._select_chunks(query, chunks)
        
        if not selected:
            return "This information is not available in our internal corpus.", []
        
        all_sentences = []
        used_chunks = []
        
        for chunk in selected:
            sentences = self._extract_answer(chunk["text"], query)
            if sentences:
                all_sentences.extend(sentences)
                used_chunks.append(chunk)
        
        if not all_sentences:
            return "This information is not available in our internal corpus.", []
        
        # Deduplicate
        unique = []
        seen = set()
        for sent in all_sentences:
            norm = sent.lower().strip()
            if norm not in seen:
                unique.append(sent)
                seen.add(norm)
        
        # Assemble (max 3)
        answer = ' '.join(unique[:3])
        
        if not answer.endswith(('.', '!', '?')):
            answer += '.'
        
        return answer, used_chunks

    # ----------------- MAIN ENTRY -----------------

    def answer_user_query(self, query: str, top_k: int = 5) -> dict:
        """Main entry point."""
        
        retrieved = self.retriever.retrieve(query, top_k=top_k)
        
        if not retrieved:
            return {
                "answer": "This information is not available in our internal corpus.",
                "citations": [],
                "mode": "offline-evaluation"
            }
        
        answer, used = self._synthesise_answer(query, retrieved)
        
        citations = " ".join(f"({c['doc_id']}: {c['section_id']})" for c in used)
        
        return {
            "answer": f"Generated in offline evaluation mode.\n\n{answer}\n\n{citations}",
            "citations": used,
            "mode": "offline-evaluation"
        }