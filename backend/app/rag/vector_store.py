"""
app/rag/vector_store.py
-----------------------
MongoDB Atlas vector storage and hybrid retrieval pipeline.
Combines Atlas Vector Search with MongoDB Text Search via Reciprocal
Rank Fusion (RRF), compatible with both existing and newly upserted chunks.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import UpdateOne
from pymongo.operations import SearchIndexModel

from app.core.config import settings
from app.db.mongodb import get_syllabus_collection, get_vector_collection, init_db_indexes
from app.rag.config import (
    HYBRID_FINAL_TOP_K,
    HYBRID_KEYWORD_TOP_K,
    HYBRID_RRF_K,
    HYBRID_VECTOR_TOP_K,
)
from app.rag.embedding import get_embedder

logger = logging.getLogger("uvicorn")

INDEX_NAME = "syllabus_vector_index"
TEXT_INDEX_NAME = "syllabus_text_index"


def _format_doc_result(doc: Dict[str, Any], score: float = 0.0) -> Dict[str, Any]:
    """Normalize fields across different document schemas."""
    meta = doc.get("metadata") or {}
    return {
        "_id": doc.get("_id"),
        "chunk_id": doc.get("chunk_id") or str(doc.get("id") or doc.get("_id")),
        "text": doc.get("text", ""),
        "chunk_type": doc.get("chunk_type") or meta.get("type") or meta.get("section") or "general",
        "page_number": doc.get("page_number") or meta.get("page") or 1,
        "semester": doc.get("semester") or meta.get("semester"),
        "course_code": doc.get("course_code") or meta.get("course_code"),
        "source_file": doc.get("source_file") or doc.get("source") or "my_college_syllabus.pdf",
        "score": score,
    }


def merge_rrf(
    vector_results: List[Dict[str, Any]],
    keyword_results: List[Dict[str, Any]],
    k: int = HYBRID_RRF_K,
    final_top_k: int = HYBRID_FINAL_TOP_K,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) combining vector and keyword search results.
    RRF Score(doc) = SUM( 1 / (k + rank_i + 1) ) for each list where doc appears.
    """
    doc_scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}

    def _get_id(doc: Dict[str, Any]) -> str:
        return str(doc.get("chunk_id") or doc.get("id") or doc.get("_id") or doc.get("text", "")[:100])

    for rank, doc in enumerate(vector_results):
        did = _get_id(doc)
        doc_scores[did] = doc_scores.get(did, 0.0) + (1.0 / (k + rank + 1))
        doc_map[did] = doc

    for rank, doc in enumerate(keyword_results):
        did = _get_id(doc)
        doc_scores[did] = doc_scores.get(did, 0.0) + (1.0 / (k + rank + 1))
        doc_map[did] = doc

    ranked_ids = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

    final_results: List[Dict[str, Any]] = []
    for did, score in ranked_ids[:final_top_k]:
        item = _format_doc_result(doc_map[did], score=score)
        item["rrf_score"] = score
        final_results.append(item)

    return final_results


async def get_existing_chunk_ids() -> set[str]:
    """Return set of chunk IDs already stored in syllabus_vectors collection."""
    collection = get_syllabus_collection()
    docs = await collection.find({}, {"chunk_id": 1, "id": 1, "_id": 1}).to_list(length=50000)
    res = set()
    for d in docs:
        if d.get("chunk_id"):
            res.add(str(d["chunk_id"]))
        if d.get("id"):
            res.add(str(d["id"]))
        if d.get("_id"):
            res.add(str(d["_id"]))
    return res


async def upsert_chunks(
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    source_file: str = "my_college_syllabus.pdf",
) -> int:
    """Store syllabus chunks and their embedding vectors in MongoDB Atlas (syllabus_vectors)."""
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunk count ({len(chunks)}) does not match embeddings count ({len(embeddings)})"
        )

    collection = get_syllabus_collection()
    operations: List[UpdateOne] = []
    now = datetime.now(timezone.utc)

    for chunk, emb in zip(chunks, embeddings):
        chunk_id = chunk["chunk_id"]
        doc = {
            "chunk_id": chunk_id,
            "id": chunk_id,
            "text": chunk["text"],
            "chunk_type": chunk.get("chunk_type", "general"),
            "page_number": chunk.get("page_number", 1),
            "semester": chunk.get("semester"),
            "course_code": chunk.get("course_code"),
            "is_global": True,
            "embedding": emb,
            "source_file": source_file,
            "created_at": now,
        }
        operations.append(
            UpdateOne(
                {"$or": [{"chunk_id": chunk_id}, {"id": chunk_id}]},
                {"$set": doc},
                upsert=True,
            )
        )

    if operations:
        result = await collection.bulk_write(operations, ordered=False)
        total = (result.upserted_count or 0) + (result.modified_count or 0)
        logger.info(f"[VectorStore] Upserted {total} syllabus chunks into syllabus_vectors")
        return total
    return 0


async def ensure_indexes() -> None:
    """Initialize text and vector search indexes for syllabus_vectors and user_documents."""
    await init_db_indexes()


async def vector_search(
    query_embedding: List[float],
    top_k: int = HYBRID_VECTOR_TOP_K,
    filter_dict: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute vector similarity search in syllabus_vectors collection."""
    collection = get_syllabus_collection()
    if collection is None:
        return []

    # 1. Try Atlas $vectorSearch pipeline stage
    try:
        pipeline: List[Dict[str, Any]] = [
            {
                "$vectorSearch": {
                    "index": INDEX_NAME,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": max(top_k * 10, 50),
                    "limit": top_k,
                }
            }
        ]
        if filter_dict:
            pipeline.append({"$match": filter_dict})

        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=top_k)
        if results:
            return [_format_doc_result(d, score=d.get("score", 0.0)) for d in results]
    except Exception as exc:
        logger.debug(f"[VectorStore] $vectorSearch aggregation note: {exc}")

    # 2. Fallback: In-memory cosine calculation over documents
    try:
        query_filter = filter_dict or {}
        docs = await collection.find(query_filter).to_list(length=500)
        if not docs:
            return []

        import numpy as np
        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return [_format_doc_result(d) for d in docs[:top_k]]

        scored: List[tuple[float, Dict[str, Any]]] = []
        for d in docs:
            emb = d.get("embedding")
            if not emb:
                continue
            d_vec = np.array(emb, dtype=np.float32)
            d_norm = np.linalg.norm(d_vec)
            sim = float(np.dot(q_vec, d_vec) / (q_norm * d_norm)) if d_norm > 0 else 0.0
            scored.append((sim, d))

        scored.sort(key=lambda x: x[0], reverse=True)
        res = []
        for sim, d in scored[:top_k]:
            res.append(_format_doc_result(d, score=sim))
        return res
    except Exception as exc:
        logger.error(f"[VectorStore] In-memory fallback failed: {exc}")
        return []


async def keyword_search(
    query_text: str,
    top_k: int = HYBRID_KEYWORD_TOP_K,
    filter_dict: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute text/keyword search using syllabus_vectors $text index, falling back to regex."""
    collection = get_syllabus_collection()
    if collection is None:
        return []

    # 1. Try $text search
    try:
        match_criteria: Dict[str, Any] = {"$text": {"$search": query_text}}
        if filter_dict:
            match_criteria.update(filter_dict)

        cursor = collection.find(
            match_criteria,
            {"score": {"$meta": "textScore"}},
        ).sort([("score", {"$meta": "textScore"})]).limit(top_k)

        results = await cursor.to_list(length=top_k)
        if results:
            return [_format_doc_result(d, score=d.get("score", 0.0)) for d in results]
    except Exception as exc:
        logger.debug(f"[VectorStore] $text search note: {exc}")

    # 2. Regex fallback for keywords
    try:
        words = [re_escape(w) for w in query_text.split() if len(w) > 3]
        if not words:
            words = [re_escape(query_text.strip())]
        pattern = "|".join(words)
        match_criteria = {"text": {"$regex": pattern, "$options": "i"}}
        if filter_dict:
            match_criteria.update(filter_dict)

        cursor = collection.find(match_criteria).limit(top_k)
        raw_results = await cursor.to_list(length=top_k)
        return [_format_doc_result(d) for d in raw_results]
    except Exception as exc:
        logger.error(f"[VectorStore] Keyword search failed: {exc}")
        return []


def re_escape(s: str) -> str:
    import re
    return re.escape(s)


class VectorStore:
    """Class interface for backward compatibility with existing tool adapters."""

    async def add(self, documents: List[str], embeddings: List[List[float]], source: str = "syllabus") -> None:
        chunks = [
            {"chunk_id": f"chunk_{i}", "text": doc, "chunk_type": "general", "page_number": 1}
            for i, doc in enumerate(documents)
        ]
        await upsert_chunks(chunks, embeddings, source_file=source)

    async def retrieve(
        self,
        query: str,
        top_k: int = HYBRID_FINAL_TOP_K,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from app.rag.embedding import embed_query

        q_emb = embed_query(query)
        vec_res = await vector_search(q_emb, top_k=HYBRID_VECTOR_TOP_K, filter_dict=where)
        kw_res = await keyword_search(query, top_k=HYBRID_KEYWORD_TOP_K, filter_dict=where)
        fused = merge_rrf(vec_res, kw_res, k=HYBRID_RRF_K, final_top_k=top_k)

        matches = []
        for doc in fused:
            matches.append({
                "text": doc.get("text", ""),
                "score": doc.get("rrf_score", 0.0),
                "source": doc.get("source_file", "my_college_syllabus.pdf"),
                "metadata": {
                    "chunk_id": doc.get("chunk_id"),
                    "page_number": doc.get("page_number"),
                    "chunk_type": doc.get("chunk_type"),
                    "semester": doc.get("semester"),
                    "course_code": doc.get("course_code"),
                },
            })
        return {"matches": matches}

    async def ensure_text_index(self) -> None:
        await ensure_indexes()

    async def ensure_vector_index(self) -> None:
        await ensure_indexes()


_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore()
    return _store_instance
