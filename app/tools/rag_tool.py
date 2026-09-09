"""
app/tools/rag_tool.py
---------------------
LangChain tools providing hybrid vector and keyword search over the
college curriculum database using the Phase 2 RAG pipeline.
"""

import asyncio
import concurrent.futures
import logging
from typing import Any, Dict

from langchain_core.tools import tool
from app.rag.rag_pipeline import run_rag_query

logger = logging.getLogger("uvicorn")


def _format_retrieval_output(result: Dict[str, Any]) -> str:
    """Format retrieved RAG chunks into clean markdown context for the LLM."""
    chunks = result.get("retrieved_chunks", [])
    if not chunks:
        return (
            "No relevant syllabus information found for your query. "
            "Please verify the course code, semester number, or topic."
        )

    formatted_sections = []
    for i, chunk in enumerate(chunks, start=1):
        page = chunk.get("page_number", "?")
        chunk_type = chunk.get("chunk_type", "general")
        semester = chunk.get("semester")
        course_code = chunk.get("course_code")

        header_parts = [f"Chunk {i}", f"Page {page}", f"Type: {chunk_type}"]
        if semester:
            header_parts.append(f"Semester {semester}")
        if course_code:
            header_parts.append(f"Course: {course_code}")

        header = f"[{' | '.join(header_parts)}]"
        content = chunk.get("text", "").strip()
        formatted_sections.append(f"{header}\n{content}")

    return "\n\n".join(formatted_sections)


async def _execute_rag_search(query: str) -> str:
    """Core async retrieval executor."""
    try:
        result = await run_rag_query(query)
        return _format_retrieval_output(result)
    except Exception as exc:
        logger.error(f"[syllabus_rag_search] Retrieval error: {exc}")
        return f"Syllabus retrieval encountered an error: {exc}"


def _run_sync(query: str) -> str:
    """Run async RAG search synchronously with threadpool event-loop isolation."""
    try:
        try:
            loop = asyncio.get_running_loop()
            in_loop = True
        except RuntimeError:
            in_loop = False

        if in_loop:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, _execute_rag_search(query))
                return future.result()
        else:
            return asyncio.run(_execute_rag_search(query))
    except Exception as exc:
        logger.error(f"[syllabus_rag_search] Sync runner error: {exc}")
        return f"Retrieval failed: {exc}"


@tool
def syllabus_rag_search(query: str) -> str:
    """
    Search the college syllabus database for course content, subjects,
    unit topics, credit distributions, course objectives, and outcomes.

    Use this tool for ANY academic question regarding:
    - Semester-wise subject lists (e.g. 'What courses are in semester 3?')
    - Course content and unit details (e.g. 'What are the topics in VLSI design?')
    - Credit structure and graduation requirements
    - Elective courses and vertical specializations
    - Laboratory courses and practical components

    Args:
        query: Natural language question about the syllabus or curriculum.

    Returns:
        Structured markdown context of retrieved syllabus chunks with page and type citations.
    """
    return _run_sync(query)


@tool
async def syllabus_rag_search_async(query: str) -> str:
    """
    Asynchronous version of syllabus_rag_search for non-blocking agent execution loops.

    Search the college syllabus database for course content, subjects,
    unit topics, credit distributions, course objectives, and outcomes.

    Args:
        query: Natural language question about the syllabus or curriculum.

    Returns:
        Structured markdown context of retrieved syllabus chunks with page and type citations.
    """
    return await _execute_rag_search(query)
