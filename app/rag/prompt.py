"""
app/rag/prompt.py
-----------------
Templates and formatting functions for constructing citation-rich RAG prompts.
"""

from typing import Any, Dict, List, Optional
from langchain_core.prompts import ChatPromptTemplate

RAG_SYSTEM_INSTRUCTION = """You are SyllabusBot, the academic assistant for Government College of Engineering (GCE), Bargur ECE Department (2022 CBCS Regulations).

Answer the student's question using ONLY the provided retrieved syllabus context below.

Rules:
1. Base your answer strictly on the provided context. If the information is not in the context, clearly say: "I couldn't find this information in the syllabus."
2. Cite the section, chunk type, and page number where appropriate (e.g. "[Page X, semester_table]").
3. For course lists: format clearly as a markdown table with columns SL.No, Course Code, Course Title, Category, Credits.
4. For course details: present Objectives, Units, and Outcomes in numbered sections.
5. Do not hallucinate course codes, credits, or topics.
"""

RAG_PROMPT_TEMPLATE = """{system_instruction}

CONTEXT (Retrieved from College Syllabus):
{context}

QUESTION:
{question}

ANSWER:"""


def format_chunks_for_context(retrieved_chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a clear, cited context block."""
    if not retrieved_chunks:
        return "No relevant syllabus chunks found."

    formatted_sections = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        page = chunk.get("page_number", "?")
        chunk_type = chunk.get("chunk_type", "general")
        sem = chunk.get("semester")
        sem_str = f" | Semester {sem}" if sem else ""
        course = chunk.get("course_code")
        course_str = f" | Course {course}" if course else ""

        header = f"--- [Source {i} | Page {page} | Type: {chunk_type}{sem_str}{course_str}] ---"
        body = chunk.get("text", "").strip()
        formatted_sections.append(f"{header}\n{body}")

    return "\n\n".join(formatted_sections)


def build_rag_prompt(query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Build complete RAG prompt text combining system instructions, formatted
    retrieved chunks, and user query.
    """
    context_block = format_chunks_for_context(retrieved_chunks)
    return RAG_PROMPT_TEMPLATE.format(
        system_instruction=RAG_SYSTEM_INSTRUCTION,
        context=context_block,
        question=query,
    )


# Backward-compatible prompt builder using ChatPromptTemplate
def build_prompt(
    context: str,
    question: str,
    intent: str = "general",
    semester: Optional[Any] = None,
    is_voice: bool = False,
):
    """LangChain ChatPromptValue builder for backwards compatibility."""
    voice_note = "Keep the answer concise (2-3 sentences), simple, and speakable without tables.\n" if is_voice else ""
    sem_label = f"Semester {semester}" if semester else "the requested semester"

    template = ChatPromptTemplate.from_messages([
        ("system", f"{RAG_SYSTEM_INSTRUCTION}\n{voice_note}"),
        ("human", "CONTEXT:\n{context}\n\nQUESTION (for {sem_label}):\n{question}\n\nANSWER:"),
    ])

    return template.format_prompt(
        context=context,
        question=question,
        sem_label=sem_label,
    )
