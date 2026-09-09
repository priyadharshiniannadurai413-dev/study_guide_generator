"""
app/rag/main.py
---------------
CLI entry point to ingest an academic syllabus PDF document end-to-end:
extracts text & tables, generates structure-aware chunks, creates Google GenAI
embeddings, upserts into MongoDB Atlas, and ensures search indexes.

Usage:
    python -m app.rag.main --file uploads/my_college_syllabus.pdf
"""

import os
import sys
import argparse
import asyncio
from collections import Counter
from pathlib import Path

# Add project root directory to sys.path to support execution as module or script
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.db.mongodb import close_mongo_connection, connect_to_mongo
from app.rag.chunking import chunk_document
from app.rag.embedding import embed_texts
from app.rag.loader import extract_pdf
from app.rag.vector_store import ensure_indexes, get_existing_chunk_ids, upsert_chunks


async def ingest_document(file_path: str) -> None:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found at: {file_path}")

    filename = os.path.basename(file_path)
    print(f"\n==================================================")
    print(f"Starting Ingestion for: {filename}")
    print(f"==================================================")

    # 0. Connect to MongoDB
    print("\n[0/5] Connecting to MongoDB Atlas...")
    await connect_to_mongo()

    try:
        # 1. Extract PDF
        print(f"\n[1/5] Extracting text and tables from {filename}...")
        pages = extract_pdf(file_path)
        print(f"[OK] Extracted {len(pages)} pages successfully.")

        # 2. Chunk Document
        print("\n[2/5] Creating structure-aware chunks...")
        chunks = chunk_document(pages)
        type_counts = Counter(c.get("chunk_type") for c in chunks)
        print(f"[OK] Created {len(chunks)} total chunks.")
        for ctype, count in type_counts.items():
            print(f"   - {ctype}: {count}")

        # Check existing chunks in MongoDB Atlas to avoid duplicate embeddings and rate limits
        existing_ids = await get_existing_chunk_ids()
        new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
        print(f"[INFO] Existing documents in Atlas: {len(existing_ids)}. New chunks to embed: {len(new_chunks)}")

        if new_chunks:
            # 3. Generate Embeddings for new chunks only
            print(f"\n[3/5] Generating embeddings for {len(new_chunks)} chunks via Google GenAI (batch size: 20)...")
            texts = [c["text"] for c in new_chunks]
            embeddings = embed_texts(texts, batch_size=20)
            print(f"[OK] Generated {len(embeddings)} embedding vectors.")

            # 4. Upsert into MongoDB
            print("\n[4/5] Upserting chunks and vectors into MongoDB Atlas...")
            stored = await upsert_chunks(new_chunks, embeddings, source_file=filename)
            print(f"[OK] Stored {stored} new documents in MongoDB Atlas vector collection.")
        else:
            print("\n[3/5 & 4/5] All chunks already indexed in MongoDB Atlas. Skipping embedding calls.")

        # 5. Ensure Search Indexes
        print("\n[5/5] Ensuring MongoDB text & vector indexes...")
        await ensure_indexes()
        print("[OK] Search indexes verified.")

        print(f"\n==================================================")
        print(f"[SUCCESS] Ingestion Complete! {len(chunks)} chunks ready for RAG.")
        print(f"==================================================")

    finally:
        await close_mongo_connection()


def main():
    parser = argparse.ArgumentParser(description="Ingest curriculum PDF into MongoDB Atlas RAG store.")
    parser.add_argument(
        "--file",
        type=str,
        default="uploads/my_college_syllabus.pdf",
        help="Path to syllabus PDF file to ingest",
    )
    args = parser.parse_args()

    asyncio.run(ingest_document(args.file))


if __name__ == "__main__":
    main()
