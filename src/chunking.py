import re


def chunk_long_text(text, chunk_size=400, overlap=60):
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
        start = end - overlap

    return chunks


def chunk_faq(text):
    pattern = r"##\s+\d+\.\s+"
    splits = re.split(pattern, text)
    headers = re.findall(pattern, text)

    chunks = []
    for i in range(1, len(splits)):
        content = headers[i - 1] + splits[i]
        chunks.append(content.strip())

    return chunks


def chunk_product_dossier(text):
    sections = re.split(r"\n##\s+", text)
    chunks = []
    for section in sections:
        cleaned = section.strip()
        if len(cleaned) > 50:
            chunks.append(cleaned)
    return chunks


def chunk_markdown_document(doc):
    filename = doc["doc_id"]
    text = doc["text"]

    if "faq" in filename.lower():
        return [{
            "doc_id": filename,
            "section_id": f"faq_{i+1}",
            "text": chunk,
            "type": "faq"
        } for i, chunk in enumerate(chunk_faq(text))]

    if "product_" in filename.lower():
        return [{
            "doc_id": filename,
            "section_id": f"section_{i+1}",
            "text": chunk,
            "type": "product"
        } for i, chunk in enumerate(chunk_product_dossier(text))]

    return [{
        "doc_id": filename,
        "section_id": f"para_{i+1}",
        "text": chunk,
        "type": "foundation"
    } for i, chunk in enumerate(chunk_long_text(text))]


def chunk_csv_rows(csv_docs):
    chunks = []
    for record in csv_docs:
        row = record["row"]
        chunks.append({
            "doc_id": record["doc_id"],
            "section_id": row.get("product_id", "unknown"),
            "text": " ".join([f"{k}: {v}" for k, v in row.items()]),
            "type": "product_catalog",
            "metadata": row
        })
    return chunks
