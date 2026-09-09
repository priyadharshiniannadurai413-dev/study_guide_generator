"""
app/rag/user_doc_service.py
----------------------------
User PDF processing and ingestion pipeline.

Extracts text and tables, chunks content semantically, computes Gemini embeddings,
and stores chunk records in the isolated `user_documents` collection strictly
tagged with the owner's `user_id`.
"""

import asyncio
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.db.mongodb import get_user_doc_collection
from app.rag.chunking import chunk_document
from app.rag.embedding import embed_texts
from app.rag.loader import extract_pdf

logger = logging.getLogger("uvicorn")


def _extract_and_chunk_pdf(file_bytes: bytes, doc_id: str, filename: str, user_id: str) -> List[Dict[str, Any]]:
    """Synchronous worker that writes temp PDF, extracts pages, and generates chunks."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        pages = extract_pdf(tmp_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError as err:
            logger.warning(f"[UserDocService] Failed to clean up temp file {tmp_path}: {err}")

    raw_chunks = chunk_document(pages)
    if not raw_chunks:
        # Fallback: if structure-aware chunker produced nothing (e.g. short document),
        # extract prose directly from pages
        all_text = "\n\n".join(p.get("text", "") for p in pages if p.get("text"))
        if all_text.strip():
            raw_chunks = [{
                "text": all_text.strip(),
                "chunk_type": "general",
                "page_number": 1,
                "chunk_id": f"{doc_id}_1",
            }]

    now = datetime.utcnow()
    records: List[Dict[str, Any]] = []

    for i, chunk in enumerate(raw_chunks, start=1):
        text = chunk.get("text", "").strip()
        if not text:
            continue

        records.append({
            "user_id": user_id,
            "doc_id": doc_id,
            "filename": filename,
            "chunk_id": f"{doc_id}_{i}",
            "text": text,
            "page_number": chunk.get("page_number", 1),
            "chunk_type": chunk.get("chunk_type", "user_content"),
            "semester": chunk.get("semester"),
            "course_code": chunk.get("course_code"),
            "created_at": now,
        })

    return records


async def process_user_pdf(
    file_bytes: bytes,
    filename: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Ingest a user-uploaded PDF into the isolated `user_documents` collection.

    Steps:
    1. Generates a unique UUID4 `doc_id`.
    2. Extracts text/tables and generates semantic chunks.
    3. Tags every chunk with {"user_id": user_id, "doc_id": doc_id, ...}.
    4. Computes dense vector embeddings using Google Gemini.
    5. Inserts all chunk records into `user_documents`.

    Args:
        file_bytes: Raw bytes of the uploaded PDF file.
        filename: Original name of the uploaded PDF file.
        user_id: Authenticated user ID (Clerk 'sub').

    Returns:
        Dict with summary: {"doc_id": str, "filename": str, "total_chunks": int}

    Raises:
        ValueError: If file is empty or contains no extractable text.
        RuntimeError: If database insertion or embedding fails.
    """
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    if not user_id:
        raise ValueError("User ID must be provided to scope document ingestion.")

    doc_id = str(uuid.uuid4())
    logger.info(f"[UserDocService] Starting ingestion for '{filename}' (doc_id={doc_id}, user={user_id})")

    # 1. Run extraction and chunking in threadpool to avoid blocking event loop
    chunk_records = await asyncio.to_thread(
        _extract_and_chunk_pdf,
        file_bytes,
        doc_id,
        filename,
        user_id,
    )

    if not chunk_records:
        raise ValueError(f"Could not extract any readable text from '{filename}'.")

    # 2. Compute embeddings for all chunks in threadpool
    texts = [record["text"] for record in chunk_records]
    logger.info(f"[UserDocService] Embedding {len(texts)} chunks for doc_id={doc_id}...")
    embeddings = await asyncio.to_thread(embed_texts, texts)

    # 3. Attach embeddings to records
    for record, emb in zip(chunk_records, embeddings):
        record["embedding"] = emb

    # 4. Insert into MongoDB collection `user_documents`
    collection = get_user_doc_collection()
    if collection is None:
        raise RuntimeError("MongoDB client is not connected.")

    await collection.insert_many(chunk_records)
    logger.info(f"[UserDocService] Successfully saved {len(chunk_records)} chunks for doc_id={doc_id}")

    return {
        "doc_id": doc_id,
        "filename": filename,
        "total_chunks": len(chunk_records),
    }
