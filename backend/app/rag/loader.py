"""
app/rag/loader.py
-----------------
Extract text and tables from academic PDF documents using pdfplumber
as primary extractor, with pypdf as a resilient fallback.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("uvicorn")


def _extract_with_pdfplumber(file_path: str) -> List[Dict[str, Any]]:
    """Fast extractor using pdfplumber extracting native text and structured tables."""
    import pdfplumber

    pages_data: List[Dict[str, Any]] = []

    with pdfplumber.open(file_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            tables_data: List[List[str]] = []

            # 1. Fast table extraction
            try:
                tables = page.find_tables()
                for table in tables:
                    extracted_table = table.extract() or []
                    table_rows = []
                    for row in extracted_table:
                        cleaned_row = [cell.strip() if cell else "" for cell in row]
                        table_rows.append(" | ".join(cleaned_row))
                    if table_rows:
                        tables_data.append(table_rows)
            except Exception:
                tables_data = []

            # 2. Fast native text extraction (bypasses slow word-by-word coordinate loop)
            raw_text = page.extract_text()
            if not raw_text or not raw_text.strip():
                logger.warning(
                    f"[RAG Loader] WARNING: Page {page_no} returned empty or whitespace-only text "
                    "(potential scanned image page with no extractable text layer)."
                )
            prose_text = (raw_text or "").strip()

            pages_data.append({
                "page_number": page_no,
                "text": prose_text,
                "tables": tables_data,
            })

    total_chars = sum(len(p.get("text", "")) for p in pages_data)
    logger.info(f"[RAG Loader - pdfplumber] Extracted {len(pages_data)} pages, total characters: {total_chars:,}.")
    return pages_data


def _extract_with_pypdf(file_path: str) -> List[Dict[str, Any]]:
    """Ultra-fast fallback extractor using pypdf."""
    from pypdf import PdfReader

    logger.info(f"[RAG Loader] Extracting with pypdf: {file_path}")
    reader = PdfReader(file_path)
    pages_data: List[Dict[str, Any]] = []

    for page_no, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text()
        if not raw_text or not raw_text.strip():
            logger.warning(
                f"[RAG Loader] WARNING: Page {page_no} returned empty or whitespace-only text "
                "(potential scanned image page with no extractable text layer)."
            )
        pages_data.append({
            "page_number": page_no,
            "text": (raw_text or "").strip(),
            "tables": [],
        })

    total_chars = sum(len(p.get("text", "")) for p in pages_data)
    logger.info(f"[RAG Loader - pypdf] Extracted {len(pages_data)} pages, total characters: {total_chars:,}.")
    return pages_data


def extract_pdf(file_path: str, prefer_fast: bool = True) -> List[Dict[str, Any]]:
    """
    Extract text and tables from a PDF document with speed-optimized fallback.
    When prefer_fast is True, uses pypdf for high throughput (under 50ms per page).

    Args:
        file_path: Path to the PDF file.
        prefer_fast: If True, uses fast pypdf extractor first.

    Returns:
        List of dicts per page: [{"page_number": int, "text": str, "tables": list}]
    """
    pages_data: List[Dict[str, Any]] = []
    if prefer_fast:
        try:
            pages_data = _extract_with_pypdf(file_path)
        except Exception as exc:
            logger.warning(f"[RAG Loader] pypdf failed ({exc}); falling back to pdfplumber")
            pages_data = _extract_with_pdfplumber(file_path)
    else:
        try:
            pages_data = _extract_with_pdfplumber(file_path)
        except Exception as exc:
            logger.warning(f"[RAG Loader] pdfplumber failed ({exc}); falling back to pypdf")
            pages_data = _extract_with_pypdf(file_path)

    total_chars = sum(len(p.get("text", "")) for p in pages_data)
    empty_pages = [p["page_number"] for p in pages_data if not p.get("text", "").strip()]
    logger.info(
        f"[RAG Loader] extract_pdf completed for '{file_path}': "
        f"Total pages: {len(pages_data)}, Total characters: {total_chars:,}, "
        f"Empty pages count: {len(empty_pages)}."
    )
    return pages_data


def is_front_matter(text: str) -> bool:
    """
    Detect non-substantive front-matter pages (copyright, license, ISBN, publisher notices, TOC).

    Returns True if at least 2 distinct front-matter cue phrases are matched or text is mostly copyright/TOC.
    """
    if not text or not text.strip():
        return True

    cues = [
        "all rights reserved",
        "license agreement",
        "isbn",
        "published by",
        "table of contents",
        "contents at a glance",
        "brief contents",
        "bentham science",
        "printed in the united states",
        "printed in",
        "end user license",
        "library of congress",
        "copyright ©",
        "copyright ©",
        "disclaimer of warranty",
        "author affiliations",
        "editorial board",
    ]
    lowered = text.lower()
    matched = sum(1 for cue in cues if cue in lowered)
    if matched >= 2:
        return True

    # Single strong cue for short copyright / EULA pages (< 300 chars)
    if len(lowered) < 400 and any(c in lowered for c in ["all rights reserved", "isbn", "license agreement", "end user license"]):
        return True

    return False


def extract_pdf_as_text(file_path: str, skip_front_matter: bool = True) -> str:
    """
    Convenience function returning full text representation of the PDF,
    formatting tables with markdown headers.

    Args:
        file_path: Path to the PDF file.
        skip_front_matter: If True, skips pages classified as front matter / licensing.
    """
    pages = extract_pdf(file_path)
    output: List[str] = []

    for page in pages:
        page_text = page.get("text", "")
        if skip_front_matter and is_front_matter(page_text):
            logger.info(f"[RAG Loader] Skipping front-matter page {page['page_number']}")
            continue
        output.append(f"\n========== PAGE {page['page_number']} ==========\n")
        if page_text:
            output.append(page_text)
        for table in page.get("tables", []):
            output.append("\n----- TABLE -----")
            output.append("\n".join(table))

    # Fallback to all pages if every page was filtered out
    if not output and pages:
        logger.warning("[RAG Loader] All pages were flagged as front matter; falling back to full extract.")
        return extract_pdf_as_text(file_path, skip_front_matter=False)

    return "\n".join(output)


def validate_and_count_pages(file_bytes: bytes, max_pages: int = 50) -> int:
    """
    In-memory page counting and validation using pypdf.
    Raises ValueError if PDF exceeds max_pages.
    """
    import io
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        if total_pages > max_pages:
            raise ValueError(f"PDF exceeds maximum page limit of {max_pages} pages (found {total_pages}).")
        return total_pages
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to inspect PDF structure or page count: {exc}")


__all__ = [
    "extract_pdf",
    "extract_pdf_as_text",
    "is_front_matter",
    "validate_and_count_pages",
]
