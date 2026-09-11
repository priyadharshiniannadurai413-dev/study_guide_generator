"""
app/rag/adhoc_loader.py
-------------------------
Ad-hoc PDF loader module for Phase 8.
Extracts text with loud diagnostics and performs generic, document-agnostic
running header and footer stripping across all pages.
"""

import logging
import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Set

from app.rag.loader import extract_pdf, extract_pdf_as_text, is_front_matter

logger = logging.getLogger("uvicorn")


def normalize_line_for_repetition(line: str) -> str:
    """
    Normalize a text line by stripping digits, collapsing excess whitespace,
    and converting to lowercase.

    Dynamic page numbers (e.g., 'Page 1 of 16' and 'Page 2 of 16') will produce
    the identical normalized pattern ('page  of ').
    Standalone page numbers (e.g., '1', '- 2 -') produce '<standalone_page_number>'.
    """
    stripped = line.strip()
    if not stripped:
        return ""

    # Standalone page number indicator
    if re.match(r"^[-—\s]*\d+[-—\s]*$", stripped):
        return "<standalone_page_number>"

    # Strip all digits
    no_digits = re.sub(r"\d+", "", stripped)
    # Collapse multiple whitespaces and lowercase
    norm = re.sub(r"\s+", " ", no_digits).strip().lower()
    return norm


def strip_repeated_headers_and_footers(
    pages: List[Dict[str, Any]],
    frequency_threshold: float = 0.50,
) -> List[Dict[str, Any]]:
    """
    Generic, document-agnostic running header and footer stripper.

    Identifies repeated running lines across pages without hardcoding any text strings:
    1. Normalizes each line by stripping digits (e.g. 'Page 1 of 12' -> 'page  of ').
    2. Counts distinct page occurrences of each non-trivial normalized line.
    3. Any normalized line appearing on > 50% of pages (and on at least 2 pages) is identified
       as a repeated header or footer.
    4. Strips those lines from every page's text before chunking.
    """
    total_pages = len(pages)
    if total_pages < 2:
        return pages

    # Count distinct pages where each normalized line appears
    page_occurrence: Dict[str, Set[int]] = defaultdict(set)
    for p_idx, page in enumerate(pages):
        text = page.get("text", "")
        lines = text.split("\n")
        for line in lines:
            norm = normalize_line_for_repetition(line)
            # Only consider non-empty normalized lines with >= 3 alphabetic chars or standalone page number
            if norm == "<standalone_page_number>" or len(re.findall(r"[a-z]", norm)) >= 3:
                page_occurrence[norm].add(p_idx)

    # Threshold for repetition: appears on more than frequency_threshold of pages
    min_pages = max(2, math.floor(total_pages * frequency_threshold) + 1)
    repeated_patterns: Set[str] = {
        norm for norm, occurrences in page_occurrence.items()
        if len(occurrences) >= min_pages
    }

    if repeated_patterns:
        sample_patterns = [p for p in repeated_patterns if p != "<standalone_page_number>"][:5]
        logger.info(
            f"[AdHocLoader] Identified {len(repeated_patterns)} repeated running header/footer pattern(s) "
            f"across {total_pages} pages (threshold: >= {min_pages} pages). Samples: {sample_patterns}"
        )
    else:
        logger.info(f"[AdHocLoader] No repeated running headers or footers detected across {total_pages} pages.")

    cleaned_pages: List[Dict[str, Any]] = []
    total_lines_stripped = 0
    for page in pages:
        page_copy = dict(page)
        text = page.get("text", "")
        lines = text.split("\n")
        surviving_lines = []
        for line in lines:
            norm = normalize_line_for_repetition(line)
            if norm in repeated_patterns:
                total_lines_stripped += 1
                continue
            surviving_lines.append(line)
        page_copy["text"] = "\n".join(surviving_lines).strip()
        cleaned_pages.append(page_copy)

    logger.info(
        f"[AdHocLoader] Stripped {total_lines_stripped} total header/footer line instances from {total_pages} pages."
    )
    return cleaned_pages


def load_adhoc_pdf(file_path: str, strip_headers_footers: bool = True) -> List[Dict[str, Any]]:
    """
    Extract text and tables from an ad-hoc uploaded PDF file.
    Logs loud warnings if any page has no extractable text.
    Applies generic header/footer stripping if enabled.
    """
    pages = extract_pdf(file_path=file_path)
    total_chars = sum(len(p.get("text", "")) for p in pages)
    empty_pages = [p["page_number"] for p in pages if not p.get("text", "").strip()]

    if empty_pages:
        logger.warning(
            f"[AdHocLoader] WARNING: Found {len(empty_pages)} empty pages out of {len(pages)} "
            f"(pages: {empty_pages[:10]}...). These may be scanned image-only pages."
        )
    else:
        logger.info(
            f"[AdHocLoader] All {len(pages)} pages extracted cleanly. Total characters: {total_chars:,}."
        )

    if strip_headers_footers and len(pages) >= 2:
        pages = strip_repeated_headers_and_footers(pages)

    return pages


__all__ = [
    "load_adhoc_pdf",
    "extract_pdf",
    "extract_pdf_as_text",
    "is_front_matter",
    "normalize_line_for_repetition",
    "strip_repeated_headers_and_footers",
]
