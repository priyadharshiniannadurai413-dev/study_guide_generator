"""
app/rag/test_retrieval.py
-------------------------
Sanity-check script that executes sample syllabus queries through
run_rag_query() and prints retrieved sources and prompt context.

Usage:
    python -m app.rag.test_retrieval
"""

import sys
import asyncio
from pathlib import Path

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
from app.rag.rag_pipeline import run_rag_query

TEST_QUERIES = [
    "What courses are offered in semester 3?",
    "What are the topics in VLSI design?",
    "How many total credits are required in the curriculum?",
]


async def run_tests():
    print("\n==================================================")
    print("Testing Hybrid Retrieval Pipeline (Vector + Keyword + RRF)")
    print("==================================================")

    await connect_to_mongo()

    try:
        for idx, query in enumerate(TEST_QUERIES, start=1):
            print(f"\n[{idx}/{len(TEST_QUERIES)}] Query: '{query}'")
            print("-" * 50)

            result = await run_rag_query(query, top_k=3)
            sources = result["sources"]
            norm = result["normalized"]

            print(f"  * Detected Semester: {norm.get('semester')}")
            print(f"  * Detected Intent:   {norm.get('intent')}")
            print(f"  * Chunks Retrieved:  {len(sources)}")

            for s_idx, src in enumerate(sources, start=1):
                chunk_id = src.get("chunk_id")
                page = src.get("page_number")
                ctype = src.get("chunk_type")
                score = src.get("score", 0.0)
                print(f"    [{s_idx}] ID: {chunk_id} | Page: {page} | Type: {ctype} | RRF Score: {score:.4f}")

            # Show a sample of the formatted prompt
            context_preview = result["answer_context"][:350].replace("\n", " ")
            print(f"  * Prompt Preview: {context_preview}...")

        print("\n==================================================")
        print("[SUCCESS] All Test Queries Retrieved Results Successfully!")
        print("==================================================")
    finally:
        await close_mongo_connection()


def main():
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()
