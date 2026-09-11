"""
app/rag/rag_pipeline.py
-----------------------
End-to-end RAG retrieval pipeline: normalizes queries, fetches from
vector and keyword indexes, fuses ranks via RRF, and formats citation prompts.
"""

import logging
from typing import Any, Dict, List

from app.rag.config import (
    HYBRID_FINAL_TOP_K,
    HYBRID_KEYWORD_TOP_K,
    HYBRID_RRF_K,
    HYBRID_VECTOR_TOP_K,
)
from app.rag.embedding import aembed_query, embed_query
from app.rag.prompt import build_prompt, build_rag_prompt
from app.rag.query_normalizer import normalize_query
from app.rag.vector_store import (
    keyword_search,
    merge_rrf,
    vector_search,
)

logger = logging.getLogger("uvicorn")


async def run_rag_query(
    query: str,
    top_k: int = HYBRID_FINAL_TOP_K,
) -> Dict[str, Any]:
    """
    Execute full standalone RAG retrieval:
      1. Normalize query & extract semester
      2. Embed query vector
      3. Run concurrent vector_search and keyword_search
      4. Reciprocal Rank Fusion (RRF)
      5. Construct citation-aware prompt context

    Args:
        query: User's syllabus question.
        top_k: Final number of ranked chunks to return.

    Returns:
        {
            "answer_context": str,
            "sources": list[dict],
            "retrieved_chunks": list[dict],
            "normalized": dict,
        }
    """
    # 1. Normalize query
    normalized = normalize_query(query)
    search_query = normalized["search_query"]
    semester = normalized.get("semester")

    filter_dict = {"semester": semester} if semester else None

    # 2. Embed query
    try:
        q_emb = await aembed_query(search_query)
    except Exception as exc:
        logger.warning(f"[RAG Pipeline] Async embed failed ({exc}); trying sync embed")
        q_emb = embed_query(search_query)

    # 3. Hybrid search (vector + keyword)
    vec_results = await vector_search(
        q_emb,
        top_k=HYBRID_VECTOR_TOP_K,
        filter_dict=filter_dict,
    )
    kw_results = await keyword_search(
        search_query,
        top_k=HYBRID_KEYWORD_TOP_K,
        filter_dict=filter_dict,
    )

    # If semester filter returned no results, broaden search without filter
    if not vec_results and not kw_results and filter_dict:
        vec_results = await vector_search(q_emb, top_k=HYBRID_VECTOR_TOP_K)
        kw_results = await keyword_search(search_query, top_k=HYBRID_KEYWORD_TOP_K)

    # 4. RRF Fusion
    fused_chunks = merge_rrf(
        vec_results,
        kw_results,
        k=HYBRID_RRF_K,
        final_top_k=top_k,
    )

    # 5. Build prompt context & sources list
    prompt_text = build_rag_prompt(query, fused_chunks)

    sources = [
        {
            "chunk_id": c.get("chunk_id"),
            "page_number": c.get("page_number"),
            "chunk_type": c.get("chunk_type"),
            "semester": c.get("semester"),
            "course_code": c.get("course_code"),
            "score": c.get("rrf_score", 0.0),
        }
        for c in fused_chunks
    ]

    return {
        "answer_context": prompt_text,
        "sources": sources,
        "retrieved_chunks": fused_chunks,
        "normalized": normalized,
    }


# Backward-compatible helpers
async def get_rag_prompt(question: str, is_voice: bool = False) -> str:
    """Return complete formatted prompt string for question."""
    result = await run_rag_query(question)
    return result["answer_context"]


async def get_rag_response(question: str, is_voice: bool = False) -> str:
    """Return formatted prompt string for question."""
    return await get_rag_prompt(question, is_voice=is_voice)
