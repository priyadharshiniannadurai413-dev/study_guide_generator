"""
app/ai/agents/curriculum/nodes/retrieve.py
---------------------------------------------
RAG retrieval node for the Curriculum agent.
Fetches relevant academic context from the vector store using the
existing hybrid search pipeline (vector + keyword + RRF fusion).
"""

import logging

from app.ai.state import SupervisorState
from app.rag.rag_pipeline import run_rag_query
from app.rag.user_doc_retriever import get_user_doc_context, format_user_doc_context

logger = logging.getLogger("uvicorn")


async def retrieve_context(state: SupervisorState) -> dict:
    """
    Retrieve relevant academic context using the RAG pipeline.

    Routes between global syllabus RAG and user-uploaded document retrieval
    based on the doc_id field in state.

    Updates:
        state["retrieved_context"] — formatted text from retrieved chunks.
    """
    user_query = state.get("user_query", "")
    doc_id = state.get("doc_id", "syllabus")
    user_id = state.get("user_id", "anonymous")

    if not user_query.strip():
        logger.warning("[CurriculumRetrieve] Empty query — returning empty context.")
        return {"retrieved_context": "No query provided."}

    try:
        if doc_id.lower() == "syllabus":
            # Global syllabus RAG pipeline
            result = await run_rag_query(user_query, top_k=6)
            chunks = result.get("retrieved_chunks", [])

            if not chunks:
                context = "No relevant syllabus information found for your query."
            else:
                sections = []
                for i, chunk in enumerate(chunks, start=1):
                    page = chunk.get("page_number", "?")
                    chunk_type = chunk.get("chunk_type", "general")
                    semester = chunk.get("semester")
                    course_code = chunk.get("course_code")

                    header_parts = [f"Source {i}", f"Page {page}", f"Type: {chunk_type}"]
                    if semester:
                        header_parts.append(f"Semester {semester}")
                    if course_code:
                        header_parts.append(f"Course: {course_code}")

                    header = f"[{' | '.join(header_parts)}]"
                    text = chunk.get("text", "").strip()
                    sections.append(f"{header}\n{text}")

                context = "\n\n".join(sections)

        else:
            # User-uploaded document retrieval
            chunks = await get_user_doc_context(
                user_id=user_id,
                doc_id=doc_id,
                query=user_query,
                top_k=8,
            )
            context = format_user_doc_context(chunks)

        logger.info(
            f"[CurriculumRetrieve] Retrieved {len(context)} chars of context "
            f"(doc_id={doc_id})."
        )
        return {"retrieved_context": context}

    except Exception as exc:
        logger.error(f"[CurriculumRetrieve] RAG retrieval failed: {exc}")
        return {
            "retrieved_context": (
                f"Retrieval error: {exc}. "
                "Please try again or rephrase your question."
            )
        }


__all__ = ["retrieve_context"]
