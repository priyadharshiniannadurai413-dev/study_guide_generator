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


def resolve_file_path(file_path: str) -> str:
    """Resolve file path across potential working directories."""
    candidates = [
        file_path,
        os.path.join(str(root_dir), file_path),
        os.path.join(str(root_dir), "uploads", os.path.basename(file_path)),
        os.path.join(str(root_dir), "backend", "uploads", os.path.basename(file_path)),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return os.path.abspath(p)
    raise FileNotFoundError(f"PDF file not found at: {file_path} (searched candidates: {candidates})")


async def ingest_document(file_path: str) -> None:
    resolved_path = resolve_file_path(file_path)
    filename = os.path.basename(resolved_path)
    print(f"\n==================================================")
    print(f"Starting Ingestion for: {filename}")
    print(f"Path: {resolved_path}")
    print(f"Target Collection: syllabus_vectors (Tier 1 Global)")
    print(f"==================================================")

    # 0. Connect to MongoDB and initialize indexes
    print("\n[0/5] Connecting to MongoDB Atlas & Initializing Schema Indexes...")
    await connect_to_mongo()

    try:
        # 1. Extract PDF
        print(f"\n[1/5] Extracting text and tables from {filename}...")
        pages = extract_pdf(resolved_path)
        print(f"[OK] Extracted {len(pages)} pages successfully.")

        # 2. Chunk Document with metadata tagging: syllabus_{page}_{idx}
        print("\n[2/5] Creating structure-aware syllabus chunks...")
        raw_chunks = chunk_document(pages)
        
        # Tag each chunk with official syllabus schema: syllabus_{page}_{idx}
        chunks = []
        for idx, c in enumerate(raw_chunks, start=1):
            page_num = c.get("page_number", 1)
            chunk_dict = {
                "chunk_id": f"syllabus_{page_num}_{idx}",
                "text": c["text"],
                "page_number": page_num,
                "chunk_type": c.get("chunk_type", "general"),
                "semester": c.get("semester"),
                "course_code": c.get("course_code"),
                "is_global": True,
            }
            chunks.append(chunk_dict)

        type_counts = Counter(c.get("chunk_type") for c in chunks)
        print(f"[OK] Created {len(chunks)} total syllabus chunks.")
        for ctype, count in type_counts.items():
            print(f"   - {ctype}: {count}")

        # Check existing chunks in MongoDB Atlas syllabus_vectors collection
        existing_ids = await get_existing_chunk_ids()
        new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
        print(f"[INFO] Existing documents in Atlas syllabus_vectors: {len(existing_ids)}. New chunks to embed: {len(new_chunks)}")

        if new_chunks:
            # 3 & 4. Embed and Upsert progressively batch-by-batch
            batch_size = 15
            total_batches = (len(new_chunks) + batch_size - 1) // batch_size
            total_stored = 0

            print(f"\n[3/5 & 4/5] Embedding and upserting {len(new_chunks)} chunks in {total_batches} batches (batch size: {batch_size})...")

            for b_idx in range(total_batches):
                start = b_idx * batch_size
                end = min(start + batch_size, len(new_chunks))
                batch = new_chunks[start:end]
                batch_texts = [c["text"] for c in batch]

                print(f" -> Batch [{b_idx + 1}/{total_batches}]: Embedding {len(batch)} chunks...")
                batch_embeddings = embed_texts(batch_texts, batch_size=batch_size)

                stored = await upsert_chunks(batch, batch_embeddings, source_file=filename)
                total_stored += stored
                print(f"    [OK] Stored {stored} chunks in syllabus_vectors. Cumulative progress: {total_stored}/{len(new_chunks)}")

                # Inter-batch delay to stay well under Google GenAI 100 RPM quota
                if b_idx + 1 < total_batches:
                    await asyncio.sleep(2.0)

            print(f"\n[OK] Successfully embedded and stored {total_stored} chunks in syllabus_vectors.")
        else:
            print("\n[3/5 & 4/5] All chunks already indexed in MongoDB Atlas syllabus_vectors. Skipping embedding calls.")

        # 5. Ensure Search Indexes
        print("\n[5/5] Ensuring MongoDB text & vector indexes across tiers...")
        await ensure_indexes()
        print("[OK] Two-tier search indexes verified.")

        print(f"\n==================================================")
        print(f"[SUCCESS] Global Syllabus Ingestion Complete! {len(chunks)} chunks ready for RAG.")
        print(f"==================================================")

    finally:
        await close_mongo_connection()


def main():
    parser = argparse.ArgumentParser(description="Ingest curriculum PDF into MongoDB Atlas syllabus_vectors store.")
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
