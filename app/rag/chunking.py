"""
app/rag/chunking.py
-------------------
Structure-aware chunking for curriculum and syllabus documents.
Extracts chunks tagged with semantic types and metadata, preserving
table structures intact while chunking long prose sections.
"""

import re
from typing import Any, Dict, List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Regex patterns for syllabus elements
COURSE_CODE_RE = re.compile(r"\b(\d{2}[A-Z]{3,5}\d{3})\b")
SEMESTER_HEADER_RE = re.compile(
    r"\bSEMESTER\s*(?:-\s*)?([IVXLCDM]+|\d+)\b", re.IGNORECASE
)

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4,
    "V": 5, "VI": 6, "VII": 7, "VIII": 8,
}


def _parse_semester(text: str) -> Optional[int]:
    """Extract semester number (1-8) if present in text."""
    match = SEMESTER_HEADER_RE.search(text)
    if not match:
        return None
    val = match.group(1).upper()
    if val.isdigit():
        sem = int(val)
        return sem if 1 <= sem <= 8 else None
    return ROMAN_TO_INT.get(val)


def _classify_chunk_type(text: str, is_table: bool = False) -> str:
    """Classify chunk into one of the required semantic types."""
    upper = text.upper()

    if "PROGRAMME OUTCOMES" in upper or "PROGRAMME SPECIFIC OUTCOMES" in upper:
        return "programme_outcome"
    if "CREDITS SUMMARY" in upper or "TOTAL CREDITS" in upper or "CREDIT DISTRIBUTION" in upper:
        return "credit_summary"
    if "ELECTIVE" in upper or "PEC" in upper or "OEC" in upper:
        return "elective"
    if is_table or "COURSE CODE" in upper or "COURSE TITLE" in upper or SEMESTER_HEADER_RE.search(upper):
        if is_table or ("SL.NO" in upper or "CREDITS" in upper):
            return "semester_table"
    if "UNIT " in upper or "UNIT-" in upper or "OBJECTIVES" in upper or "OUTCOMES" in upper or COURSE_CODE_RE.search(text):
        return "unit_content"

    return "general"


def chunk_document(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Perform structure-aware chunking on extracted PDF pages.

    Args:
        pages: List of dicts per page from extract_pdf:
               [{"page_number": int, "text": str, "tables": list[list[str]]}]

    Returns:
        List of chunk dicts:
        [
            {
                "text": str,
                "chunk_type": str,
                "page_number": int,
                "chunk_id": str,
                "semester": int | None,
                "course_code": str | None,
            }
        ]
    """
    chunks: List[Dict[str, Any]] = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    current_semester: Optional[int] = None

    for page in pages:
        page_num = page.get("page_number", 1)
        prose_text = page.get("text", "")
        tables = page.get("tables", [])

        # Check if this page sets or updates the current semester
        detected_sem = _parse_semester(prose_text)
        if detected_sem:
            current_semester = detected_sem

        # 1. Process tables first — keep table chunks whole (never split mid-table)
        for t_idx, table_rows in enumerate(tables, start=1):
            table_str = "\n".join(table_rows).strip()
            if not table_str:
                continue

            table_sem = _parse_semester(table_str) or current_semester
            chunk_type = _classify_chunk_type(table_str, is_table=True)
            course_match = COURSE_CODE_RE.search(table_str)
            course_code = course_match.group(1) if course_match else None

            chunk_id = f"doc_p{page_num}_tbl_{t_idx}"
            chunks.append({
                "text": table_str,
                "chunk_type": chunk_type,
                "page_number": page_num,
                "chunk_id": chunk_id,
                "semester": table_sem,
                "course_code": course_code,
            })

        # 2. Process prose text
        if not prose_text.strip():
            continue

        prose_sections = text_splitter.split_text(prose_text)
        for s_idx, section in enumerate(prose_sections, start=1):
            sec_clean = section.strip()
            if not sec_clean:
                continue

            sec_sem = _parse_semester(sec_clean) or current_semester
            chunk_type = _classify_chunk_type(sec_clean, is_table=False)
            course_match = COURSE_CODE_RE.search(sec_clean)
            course_code = course_match.group(1) if course_match else None

            chunk_id = f"doc_p{page_num}_sec_{s_idx}"
            chunks.append({
                "text": sec_clean,
                "chunk_type": chunk_type,
                "page_number": page_num,
                "chunk_id": chunk_id,
                "semester": sec_sem,
                "course_code": course_code,
            })

    return chunks
