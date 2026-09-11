"""
app/ai/agents/mcq/nodes/retrieve.py
---------------------------------------
RAG retrieval node for the MCQ agent.
Fetches academic context for quiz generation.
"""

import logging

from app.ai.state import SupervisorState
from app.rag.rag_pipeline import run_rag_query
from app.rag.user_doc_retriever import get_user_doc_context, format_user_doc_context

logger = logging.getLogger("uvicorn")


async def retrieve_context(state: SupervisorState) -> dict:
    """
    Retrieve academic context for MCQ generation.

    Uses broad retrieval (top_k=8) to gather diverse material
    for generating varied quiz questions.

    Updates:
        state["retrieved_context"] — formatted text from retrieved chunks.
    """
    user_query = state.get("user_query", "")
    doc_id = state.get("doc_id", "syllabus")
    user_id = state.get("user_id", "anonymous")

    # Broaden the search for MCQ material
    search_query = user_query if len(user_query.split()) > 3 else (
        f"{user_query} key topics, definitions, formulas, and important concepts"
    )

    try:
        if doc_id.lower() == "syllabus":
            result = await run_rag_query(search_query, top_k=8)
            chunks = result.get("retrieved_chunks", [])

            if not chunks:
                context = "No relevant academic content found for MCQ generation."
            else:
                sections = []
                for i, chunk in enumerate(chunks, start=1):
                    page = chunk.get("page_number", "?")
                    text = chunk.get("text", "").strip()
                    sections.append(f"[Page {page}]\n{text}")
                context = "\n\n".join(sections)
        else:
            chunks = await get_user_doc_context(
                user_id=user_id,
                doc_id=doc_id,
                query=search_query,
                top_k=10,
            )
            context = format_user_doc_context(chunks)

        logger.info(
            f"[MCQRetrieve] Retrieved {len(context)} chars of context "
            f"(doc_id={doc_id})."
        )
        return {"retrieved_context": context}

    except Exception as exc:
        logger.error(f"[MCQRetrieve] RAG retrieval failed: {exc}")
        return {
            "retrieved_context": f"Retrieval error: {exc}."
        }


__all__ = ["retrieve_context"]
