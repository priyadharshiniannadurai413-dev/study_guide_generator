"""
app/rag/user_doc_retriever.py
------------------------------
User document vector retriever with strict tenant isolation.
Enforces hard filtering on `user_id` and `doc_id` so student uploads remain
completely isolated per user and never touch the global syllabus collection.
"""

import asyncio
import logging
import math
from typing import Any, Dict, List

from app.db.mongodb import get_user_doc_collection
from app.rag.embedding import embed_query

logger = logging.getLogger("uvicorn")


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two numerical vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a, b in zip(vec_a, vec_b)))
    norm_b = math.sqrt(sum(b * b for a, b in zip(vec_a, vec_b)))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


async def _atlas_vector_search(
    collection: Any,
    query_vector: List[float],
    user_id: str,
    doc_id: str,
    top_k: int,
) -> List[Dict[str, Any]]:
    """Attempt MongoDB Atlas native $vectorSearch with hard user_id/doc_id filters."""
    pipeline = [
        {
            "$vectorSearch": {
                "index": "user_vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": top_k * 10,
                "limit": top_k,
                "filter": {
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"doc_id": {"$eq": doc_id}},
                    ]
                },
            }
        },
        {
            "$project": {
                "text": 1,
                "page_number": 1,
                "chunk_id": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    cursor = collection.aggregate(pipeline)
    return await cursor.to_list(length=top_k)


async def _in_memory_similarity_search(
    collection: Any,
    query_vector: List[float],
    user_id: str,
    doc_id: str,
    top_k: int,
) -> List[Dict[str, Any]]:
    """
    Fallback exact vector similarity search.
    Strictly queries documents matching {"user_id": user_id, "doc_id": doc_id},
    computes cosine similarity in-memory, and returns the top-k highest scoring chunks.
    """
    cursor = collection.find(
        {"user_id": user_id, "doc_id": doc_id},
        {"text": 1, "page_number": 1, "chunk_id": 1, "embedding": 1},
    )
    docs = await cursor.to_list(length=1000)
    if not docs:
        return []

    scored_chunks = []
    for doc in docs:
        emb = doc.get("embedding")
        if not emb:
            continue
        sim = _cosine_similarity(query_vector, emb)
        scored_chunks.append({
            "text": doc.get("text", ""),
            "page_number": doc.get("page_number", 1),
            "chunk_id": doc.get("chunk_id", ""),
            "score": round(sim, 4),
        })

    # Sort descending by similarity score
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]


async def get_user_doc_context(
    user_id: str,
    doc_id: str,
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant chunks from a user's uploaded document strictly filtered
    by `user_id` and `doc_id`.

    Args:
        user_id: Clerk user identifier ('sub').
        doc_id: UUID of the uploaded document.
        query: User's question or search prompt.
        top_k: Number of most similar chunks to return (default: 5).

    Returns:
        List of dicts:
        [{"text": str, "page_number": int, "chunk_id": str, "score": float}, ...]
    """
    if not user_id or not doc_id:
        logger.warning("[UserDocRetriever] user_id or doc_id missing — returning empty context")
        return []

    if not query or not query.strip():
        logger.warning("[UserDocRetriever] Query is empty — returning empty context")
        return []

    collection = get_user_doc_collection()
    if collection is None:
        logger.error("[UserDocRetriever] MongoDB collection not available")
        return []

    # 1. Generate dense query embedding
    query_vector = await asyncio.to_thread(embed_query, query)

    # 2. Query MongoDB with Atlas vector search, falling back to exact cosine ranking
    try:
        results = await _atlas_vector_search(collection, query_vector, user_id, doc_id, top_k)
        if results:
            return results
    except Exception as atlas_err:
        logger.info(f"[UserDocRetriever] Atlas $vectorSearch unavailable ({atlas_err}); using direct cosine search.")

    return await _in_memory_similarity_search(collection, query_vector, user_id, doc_id, top_k)


def format_user_doc_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved user document chunks into markdown context for LLM generation."""
    if not chunks:
        return "No relevant content found in the selected document."

    sections = []
    for i, c in enumerate(chunks, start=1):
        page = c.get("page_number", "?")
        text = c.get("text", "").strip()
        sections.append(f"[Excerpt {i} | Page {page}]\n{text}")

    return "\n\n".join(sections)
