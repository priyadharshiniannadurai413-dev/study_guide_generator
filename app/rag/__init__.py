"""
app/rag
-------
RAG subsystem: loader, chunker, embedder, vector store, normalizer,
prompt builder, and pipeline orchestrator.
"""

from .chunking import chunk_document
from .config import (
    HYBRID_FINAL_TOP_K,
    HYBRID_KEYWORD_TOP_K,
    HYBRID_RRF_K,
    HYBRID_VECTOR_TOP_K,
)
from .embedding import aembed_query, embed_query, embed_texts, get_embedder
from .loader import extract_pdf, extract_pdf_as_text
from .prompt import build_rag_prompt
from .query_normalizer import normalize_query
from .rag_pipeline import run_rag_query
from .vector_store import (
    VectorStore,
    ensure_indexes,
    get_vector_store,
    keyword_search,
    merge_rrf,
    upsert_chunks,
    vector_search,
)

__all__ = [
    "extract_pdf",
    "extract_pdf_as_text",
    "chunk_document",
    "get_embedder",
    "embed_texts",
    "embed_query",
    "aembed_query",
    "upsert_chunks",
    "ensure_indexes",
    "vector_search",
    "keyword_search",
    "merge_rrf",
    "VectorStore",
    "get_vector_store",
    "normalize_query",
    "build_rag_prompt",
    "run_rag_query",
    "HYBRID_VECTOR_TOP_K",
    "HYBRID_KEYWORD_TOP_K",
    "HYBRID_FINAL_TOP_K",
    "HYBRID_RRF_K",
]
