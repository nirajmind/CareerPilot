import os
import uuid
from .mongo_vector import upsert_document
from app.gemini.service import GeminiService

gemini_service = GeminiService()

def ingest_text(text: str, metadata: dict = None):
    """Ingest a single text chunk into MongoDB vector store."""
    doc_id = str(uuid.uuid4())
    embedding = gemini_service.embed(text)

    upsert_document(
        doc_id=doc_id,
        text=text,
        embedding=embedding,
        metadata=metadata
    )

    return doc_id


def ingest_file(filepath: str):
    """Ingest a text file into the vector store."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    return ingest_text(content, metadata={"source": filepath})