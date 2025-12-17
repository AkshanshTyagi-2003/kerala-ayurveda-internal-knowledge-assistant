import re


def chunk_foundation(text):
    """
    Chunk foundation documents by H2 sections, not paragraphs.
    This keeps prose + bullets together.
    """
    # Split by H2 headers (##)
    sections = re.split(r'\n##\s+', text)
    chunks = []
    
    for section in sections:
        section = section.strip()
        # Keep substantial sections
        if len(section) >= 150:
            chunks.append(section)
    
    # If no H2 splits worked, fall back to paragraphs
    if not chunks:
        paragraphs = re.split(r"\n\s*\n", text)
        for p in paragraphs:
            p = p.strip()
            if len(p) >= 150:
                chunks.append(p)
    
    return chunks


def chunk_dosha_guide(text):
    """
    Split by H2 headers - each dosha section becomes one chunk.
    """
    sections = re.split(r"\n##\s+", text)
    chunks = []

    for section in sections:
        section = section.strip()
        if len(section) >= 100:
            chunks.append(section)

    return chunks


def chunk_faq(text):
    """
    Each Q&A pair becomes one chunk.
    """
    pattern = r"(##\s+\d+\.\s+[^\n]+)"
    parts = re.split(pattern, text)

    chunks = []
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            question = parts[i].strip()
            answer = parts[i + 1].strip()
            combined = f"{question}\n\n{answer}"
            if len(combined) >= 100:
                chunks.append(combined)

    return chunks


def chunk_product_dossier(text):
    """
    Split product dossiers by H2 sections.
    """
    sections = re.split(r"\n##\s+", text)
    chunks = []

    for section in sections:
        section = section.strip()
        if len(section) >= 100:
            chunks.append(section)

    return chunks


def chunk_markdown_document(doc):
    """
    Route to appropriate chunking strategy based on document type.
    """
    filename = doc["doc_id"].lower()
    text = doc["text"]

    # Dosha guide
    if "dosha" in filename:
        chunks = chunk_dosha_guide(text)
        return [{
            "doc_id": doc["doc_id"],
            "section_id": f"dosha_{i+1}",
            "text": c,
            "type": "dosha"
        } for i, c in enumerate(chunks)]

    # FAQ
    if "faq" in filename:
        chunks = chunk_faq(text)
        return [{
            "doc_id": doc["doc_id"],
            "section_id": f"faq_{i+1}",
            "text": c,
            "type": "faq"
        } for i, c in enumerate(chunks)]

    # Product dossiers
    if any(name in filename for name in ["product_", "ashwagandha", "triphala", "brahmi"]):
        chunks = chunk_product_dossier(text)
        return [{
            "doc_id": doc["doc_id"],
            "section_id": f"section_{i+1}",
            "text": c,
            "type": "product"
        } for i, c in enumerate(chunks)]

    # Clinic/treatment programs
    if "clinic" in filename or "program" in filename or "treatment" in filename:
        chunks = chunk_product_dossier(text)
        return [{
            "doc_id": doc["doc_id"],
            "section_id": f"section_{i+1}",
            "text": c,
            "type": "program"
        } for i, c in enumerate(chunks)]

    # Foundation documents - USE H2 SPLITTING, NOT PARAGRAPHS
    chunks = chunk_foundation(text)
    return [{
        "doc_id": doc["doc_id"],
        "section_id": f"section_{i+1}",
        "text": c,
        "type": "foundation"
    } for i, c in enumerate(chunks)]


def chunk_csv_rows(csv_docs):
    """
    Convert each CSV row to a readable text chunk.
    """
    chunks = []
    
    for record in csv_docs:
        row = record["row"]
        
        # Build natural language description
        parts = []
        
        if "name" in row and row["name"]:
            parts.append(f"{row['name']}")
        
        if "category" in row and row["category"]:
            parts.append(f"is in the {row['category']} category")
        
        if "target_concerns" in row and row["target_concerns"]:
            parts.append(f"and is used for {row['target_concerns']}")
        
        if "key_herbs" in row and row["key_herbs"]:
            parts.append(f"It contains {row['key_herbs']}")
        
        if "contraindications_short" in row and row["contraindications_short"]:
            parts.append(f"Please note: {row['contraindications_short']}")
        
        text = ". ".join(parts)
        if text and not text.endswith('.'):
            text += '.'
        
        chunks.append({
            "doc_id": record["doc_id"],
            "section_id": str(row.get("product_id", "unknown")),
            "text": text,
            "type": "product_catalog",
            "metadata": row
        })

    return chunks