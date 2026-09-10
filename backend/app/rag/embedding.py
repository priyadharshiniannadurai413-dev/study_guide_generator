"""
app/rag/embedding.py
--------------------
Singleton wrapper around GoogleGenerativeAIEmbeddings with batching,
384-dimension output matching Atlas vector index, and exponential
backoff retry for rate limits.
"""

import os
import time
import logging
from typing import List, Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

logger = logging.getLogger("uvicorn")

_embedder: Optional[GoogleGenerativeAIEmbeddings] = None
DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
DEFAULT_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))


def get_embedder(
    model_name: str = DEFAULT_MODEL,
    dimension: int = DEFAULT_DIMENSION,
) -> GoogleGenerativeAIEmbeddings:
    """Return a cached, lazy-initialized GoogleGenerativeAIEmbeddings instance."""
    global _embedder
    if _embedder is None:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured in settings/.env — cannot initialize embedder."
            )
        _embedder = GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=api_key,
            output_dimensionality=dimension,
        )
    return _embedder


def _embed_batch_with_retry(
    embedder: GoogleGenerativeAIEmbeddings,
    batch: List[str],
    max_retries: int = 3,
) -> List[List[float]]:
    """Embed a small batch with retry on rate limits (429)."""
    for attempt in range(1, max_retries + 1):
        try:
            return embedder.embed_documents(batch)
        except Exception as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                sleep_secs = 20 * attempt
                logger.warning(
                    f"[Embedding] Rate limit hit (attempt {attempt}/{max_retries}). "
                    f"Waiting {sleep_secs}s before retry..."
                )
                print(f"   [WARN] Rate limit hit. Waiting {sleep_secs}s before retry...")
                time.sleep(sleep_secs)
            else:
                raise exc
    return embedder.embed_documents(batch)


def embed_texts(texts: List[str], batch_size: int = 20) -> List[List[float]]:
    """
    Convert document chunks into embeddings using batching and rate-limit retries.

    Args:
        texts: List of text strings to embed.
        batch_size: Texts per API call (default 20 to avoid free-tier TPM burst limits).

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []

    embedder = get_embedder()
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_emb = _embed_batch_with_retry(embedder, batch)
        all_embeddings.extend(batch_emb)
        # Gentle delay between batches to respect 100 RPM quota
        if i + batch_size < len(texts):
            time.sleep(1.0)

    return all_embeddings


async def aembed_texts(texts: List[str], batch_size: int = 20) -> List[List[float]]:
    """Async variant of embed_texts."""
    return embed_texts(texts, batch_size=batch_size)


def embed_query(text: str) -> List[float]:
    """Convert single query into an embedding vector."""
    embedder = get_embedder()
    for attempt in range(1, 4):
        try:
            return embedder.embed_query(text)
        except Exception as exc:
            if ("429" in str(exc) or "quota" in str(exc).lower()) and attempt < 3:
                time.sleep(5 * attempt)
            else:
                raise exc
    return embedder.embed_query(text)


async def aembed_query(text: str) -> List[float]:
    """Async conversion of single query into embedding vector."""
    return embed_query(text)


# Backward-compatibility class and helper for existing call patterns
class EmbeddingModel:
    def __init__(self, model_name: str = DEFAULT_MODEL, dimension: int = DEFAULT_DIMENSION):
        self.embeddings = get_embedder(model_name, dimension)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return embed_texts(texts)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return embed_texts(texts)

    def embed_query(self, text: str) -> List[float]:
        return embed_query(text)


def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel()
