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
    """Primary extractor using pdfplumber with table bounding-box isolation."""
    import pdfplumber

    pages_data: List[Dict[str, Any]] = []

    with pdfplumber.open(file_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            tables_data: List[List[str]] = []
            table_boxes = []

            # 1. Detect and extract table data
            tables = page.find_tables()
            for table in tables:
                table_boxes.append(table.bbox)
                extracted_table = table.extract() or []
                table_rows = []
                for row in extracted_table:
                    cleaned_row = [cell.strip() if cell else "" for cell in row]
                    table_rows.append(" | ".join(cleaned_row))
                if table_rows:
                    tables_data.append(table_rows)

            # 2. Extract prose words outside table bounding boxes
            words = page.extract_words() or []
            outside_words = []
            for word in words:
                x = word["x0"]
                y = word["top"]
                inside_table = False
                for bbox in table_boxes:
                    x0, top, x1, bottom = bbox
                    if x0 <= x <= x1 and top <= y <= bottom:
                        inside_table = True
                        break
                if not inside_table:
                    outside_words.append(word)

            # 3. Group prose words into lines by vertical position
            lines: Dict[int, List[Dict[str, Any]]] = {}
            for word in outside_words:
                key = round(word["top"])
                lines.setdefault(key, []).append(word)

            prose_lines = []
            for top in sorted(lines.keys()):
                line = sorted(lines[top], key=lambda w: w["x0"])
                text = " ".join(word["text"] for word in line).strip()
                if text:
                    prose_lines.append(text)

            prose_text = "\n".join(prose_lines).strip()

            pages_data.append({
                "page_number": page_no,
                "text": prose_text,
                "tables": tables_data,
            })

    return pages_data


def _extract_with_pypdf(file_path: str) -> List[Dict[str, Any]]:
    """Fallback extractor using pypdf."""
    from pypdf import PdfReader

    logger.warning(f"[RAG Loader] Falling back to pypdf for {file_path}")
    reader = PdfReader(file_path)
    pages_data: List[Dict[str, Any]] = []

    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages_data.append({
            "page_number": page_no,
            "text": text.strip(),
            "tables": [],
        })

    return pages_data


def extract_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract text and tables from a PDF document.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of dicts per page: [{"page_number": int, "text": str, "tables": list}]
    """
    try:
        return _extract_with_pdfplumber(file_path)
    except Exception as exc:
        logger.error(f"[RAG Loader] pdfplumber failed ({exc}); trying pypdf fallback")
        return _extract_with_pypdf(file_path)


def extract_pdf_as_text(file_path: str) -> str:
    """
    Convenience function returning full text representation of the PDF,
    formatting tables with markdown headers.
    """
    pages = extract_pdf(file_path)
    output: List[str] = []

    for page in pages:
        output.append(f"\n========== PAGE {page['page_number']} ==========\n")
        if page["text"]:
            output.append(page["text"])
        for table in page["tables"]:
            output.append("\n----- TABLE -----")
            output.append("\n".join(table))

    return "\n".join(output)
