import os
import pandas as pd

DATA_DIR = "data"


def load_markdown_files():
    documents = []
    for file in os.listdir(DATA_DIR):
        if file.endswith(".md"):
            path = os.path.join(DATA_DIR, file)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            documents.append({
                "doc_id": file,
                "type": "markdown",
                "text": text
            })
    return documents


def load_product_catalog():
    path = os.path.join(DATA_DIR, "products_catalog.csv")
    df = pd.read_csv(path)
    records = []
    for _, row in df.iterrows():
        records.append({
            "doc_id": "products_catalog.csv",
            "type": "csv",
            "row": row.to_dict()
        })
    return records


def load_all_documents():
    md_docs = load_markdown_files()
    csv_docs = load_product_catalog()
    return md_docs, csv_docs
