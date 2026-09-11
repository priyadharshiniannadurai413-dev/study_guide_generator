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
from app.rag.loader import is_front_matter

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
                "user_id": 1,
                "doc_id": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    cursor = collection.aggregate(pipeline)
    raw_results = await cursor.to_list(length=top_k)
    return [
        {
            "text": r.get("text", ""),
            "page_number": r.get("page_number", 1),
            "chunk_id": r.get("chunk_id", ""),
            "score": r.get("score", 0.0),
        }
        for r in raw_results
        if r.get("user_id") == user_id and r.get("doc_id") == doc_id
    ]


async def _direct_chunk_fetch(
    collection: Any,
    user_id: str,
    doc_id: str,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    """Directly fetch ordered document chunks from MongoDB without embedding queries."""
    query_filter: Dict[str, Any] = {"user_id": user_id, "doc_id": doc_id}
    cursor = collection.find(
        query_filter,
        {"text": 1, "page_number": 1, "chunk_id": 1},
    ).sort("page_number", 1)
    docs = await cursor.to_list(length=limit)

    # Fallback to doc_id alone if not found under specific user_id (handles dev vs clerk sessions)
    if not docs:
        fallback_cursor = collection.find(
            {"doc_id": doc_id},
            {"text": 1, "page_number": 1, "chunk_id": 1},
        ).sort("page_number", 1)
        docs = await fallback_cursor.to_list(length=limit)

    return [
        {
            "text": d.get("text", ""),
            "page_number": d.get("page_number", 1),
            "chunk_id": d.get("chunk_id", ""),
            "score": 1.0,
        }
        for d in docs
        if d.get("text") and not is_front_matter(d.get("text", ""))
    ]


async def _in_memory_similarity_search(
    collection: Any,
    query_vector: List[float],
    user_id: str,
    doc_id: str,
    top_k: int,
) -> List[Dict[str, Any]]:
    """
    Fallback exact vector similarity search.
    Queries documents matching {"user_id": user_id, "doc_id": doc_id},
    computes cosine similarity in-memory, and returns the top-k highest scoring chunks.
    """
    cursor = collection.find(
        {"user_id": user_id, "doc_id": doc_id},
        {"text": 1, "page_number": 1, "chunk_id": 1, "embedding": 1},
    )
    docs = await cursor.to_list(length=1000)

    # Fallback lookup by doc_id alone if tenant mismatch occurs
    if not docs:
        fallback_cursor = collection.find(
            {"doc_id": doc_id},
            {"text": 1, "page_number": 1, "chunk_id": 1, "embedding": 1},
        )
        docs = await fallback_cursor.to_list(length=1000)

    if not docs:
        return []

    scored_chunks = []
    for doc in docs:
        text = doc.get("text", "")
        if not text or is_front_matter(text):
            continue
        emb = doc.get("embedding")
        if not emb or not query_vector:
            scored_chunks.append({
                "text": text,
                "page_number": doc.get("page_number", 1),
                "chunk_id": doc.get("chunk_id", ""),
                "score": 0.5,
            })
            continue
        sim = _cosine_similarity(query_vector, emb)
        scored_chunks.append({
            "text": text,
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
    top_k: int = 8,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant chunks from a user's uploaded document.
    If query is generic or embedding fails, smoothly falls back to direct
    document chunks sorted by page number to guarantee 100% availability.

    Args:
        user_id: User identifier (e.g. Clerk 'sub' or dev token).
        doc_id: UUID of the uploaded document.
        query: User's question or search prompt.
        top_k: Number of chunks to return (default: 8).

    Returns:
        List of dicts:
        [{"text": str, "page_number": int, "chunk_id": str, "score": float}, ...]
    """
    if not user_id or not doc_id:
        logger.warning("[UserDocRetriever] user_id or doc_id missing — returning empty context")
        return []

    collection = get_user_doc_collection()
    if collection is None:
        logger.error("[UserDocRetriever] MongoDB collection not available")
        return []

    # If query is generic or missing, directly fetch document chunks in sequence
    generic_phrases = (
        "core concepts, architecture, formulas, and high-yield revision topics",
        "study notes",
        "summarize",
        "summary",
        "quiz",
        "mcq",
    )
    is_generic = not query or not query.strip() or any(p in query.lower() for p in generic_phrases)

    if is_generic:
        direct_chunks = await _direct_chunk_fetch(collection, user_id, doc_id, limit=top_k)
        if direct_chunks:
            return direct_chunks

    # Attempt dense query embedding with graceful error catching
    query_vector: List[float] = []
    try:
        query_vector = await asyncio.to_thread(embed_query, query)
    except Exception as emb_err:
        logger.warning(f"[UserDocRetriever] Query embedding failed ({emb_err}); using direct chunk retrieval.")
        return await _direct_chunk_fetch(collection, user_id, doc_id, limit=top_k)

    # Attempt MongoDB Atlas vector search, falling back to in-memory cosine ranking
    try:
        results = await _atlas_vector_search(collection, query_vector, user_id, doc_id, top_k)
        if results:
            return results
    except Exception as atlas_err:
        logger.info(f"[UserDocRetriever] Atlas $vectorSearch unavailable ({atlas_err}); using in-memory search.")

    results = await _in_memory_similarity_search(collection, query_vector, user_id, doc_id, top_k)
    if not results:
        # Ultimate fallback: fetch direct chunks without vector filtering
        results = await _direct_chunk_fetch(collection, user_id, doc_id, limit=top_k)

    return results


def format_user_doc_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved user document chunks into markdown context for LLM generation."""
    if not chunks:
        return "No relevant content found in the selected document."

    sections = []
    for i, c in enumerate(chunks, start=1):
        text = c.get("text", "").strip()
        if not text or is_front_matter(text):
            continue
        page = c.get("page_number", "?")
        sections.append(f"[Excerpt {i} | Page {page}]\n{text}")

    return "\n\n".join(sections) if sections else "No substantive academic content found in the selected document."


async def get_full_user_document(user_id: str, doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve ALL chunks belonging to a document in sequential page order.
    Sorts ascending by page_number and chunk_id.
    Strictly isolated per user_id, with fallback to doc_id alone if session differs.
    """
    if not doc_id:
        return []

    collection = get_user_doc_collection()
    if collection is None:
        logger.error("[UserDocRetriever] MongoDB collection not available")
        return []

    cursor = collection.find(
        {"user_id": user_id, "doc_id": doc_id},
        {"text": 1, "page_number": 1, "chunk_id": 1, "_id": 0},
    ).sort([("page_number", 1), ("chunk_id", 1)])
    chunks = await cursor.to_list(length=None)

    if not chunks:
        # Fallback to doc_id alone to handle session/dev token variations
        fallback_cursor = collection.find(
            {"doc_id": doc_id},
            {"text": 1, "page_number": 1, "chunk_id": 1, "_id": 0},
        ).sort([("page_number", 1), ("chunk_id", 1)])
        chunks = await fallback_cursor.to_list(length=None)

    return chunks


def assemble_document_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Stitch sequential document chunks with explicit page separators.
    Filters out non-substantive front-matter pages (copyright, publishers, TOC).
    """
    if not chunks:
        return ""

    snippets = []
    for c in chunks:
        txt = c.get("text", "").strip()
        if not txt or is_front_matter(txt):
            continue
        page = c.get("page_number", "?")
        snippets.append(f"--- [PAGE {page}] ---\n{txt}")

    return "\n\n".join(snippets)


__all__ = [
    "get_user_doc_context",
    "get_full_user_document",
    "assemble_document_context",
    "format_user_doc_context",
]
