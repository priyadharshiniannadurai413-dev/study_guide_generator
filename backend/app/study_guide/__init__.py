"""
app/study_guide
---------------
Ad-hoc PDF study guide package (Phase 8).
Provides Map-Reduce summarization and distributed MCQ generation for arbitrarily long documents.
"""

from .summarizer import summarize_document, summarize_document_async
from .mcq_generator import generate_mcqs_for_document, generate_mcqs_for_document_async

__all__ = [
    "summarize_document",
    "summarize_document_async",
    "generate_mcqs_for_document",
    "generate_mcqs_for_document_async",
]
