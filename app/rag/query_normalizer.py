"""
app/rag/query_normalizer.py
---------------------------
Normalizes free-form user questions by stripping conversational filler,
extracting academic semester numbers (as integers), and detecting intent.
"""

import re
from typing import Any, Dict, Optional

# Mappings for semester extraction
ARABIC_TO_INT = {
    "1": 1, "2": 2, "3": 3, "4": 4,
    "5": 5, "6": 6, "7": 7, "8": 8,
}

WORD_TO_INT = {
    "first": 1,   "1st": 1,
    "second": 2,  "2nd": 2,
    "third": 3,   "3rd": 3,
    "fourth": 4,  "4th": 4,
    "fifth": 5,   "5th": 5,
    "sixth": 6,   "6th": 6,
    "seventh": 7, "7th": 7,
    "eighth": 8,  "8th": 8,
}

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4,
    "V": 5, "VI": 6, "VII": 7, "VIII": 8,
}

SEM_REGEX = re.compile(
    r"(?:"
    r"(?P<word>first|second|third|fourth|fifth|sixth|seventh|eighth|1st|2nd|3rd|4th|5th|6th|7th|8th)\s+sem(?:ester)?"
    r"|sem(?:ester)?\s*[-]?\s*(?P<roman>[IVXLCDM]{1,8})\b"
    r"|sem(?:ester)?\s*(?:no\.?|number)?\s*(?P<arabic>[1-8])\b"
    r"|\b(?P<standalone_digit>[1-8])(?:st|nd|rd|th)?\s+sem(?:ester)?\b"
    r")",
    re.IGNORECASE,
)

FILLER_PATTERNS = re.compile(
    r"\b(please|can\s+you\s+(?:tell|show|give)\s+me|tell\s+me|give\s+me|i\s+want\s+to\s+know|"
    r"what\s+is\s+the|what\s+are\s+the|show\s+me|could\s+you|kindly)\b",
    re.IGNORECASE,
)

INTENT_CREDIT_INFO = re.compile(r"\b(credits?|total\s+credits?|how\s+many\s+credits?)\b", re.IGNORECASE)
INTENT_LIST_COURSES = re.compile(r"\b(courses?|subjects?|papers?|list|what\s+courses?|offered|curriculum)\b", re.IGNORECASE)
INTENT_UNIT = re.compile(r"\b(unit\s*[1-6]|module\s*[1-6]|topics?\s+in\s+unit)\b", re.IGNORECASE)
INTENT_OBJECTIVES = re.compile(r"\b(objectives?)\b", re.IGNORECASE)
INTENT_OUTCOMES = re.compile(r"\b(outcomes?)\b", re.IGNORECASE)
INTENT_COURSE_DETAIL = re.compile(r"\b(syllabus|topics?|content|explain\s+course)\b", re.IGNORECASE)


def extract_semester(query: str) -> Optional[int]:
    """Extract semester number as an integer (1-8) from query."""
    match = SEM_REGEX.search(query)
    if not match:
        return None

    if match.group("word"):
        return WORD_TO_INT.get(match.group("word").lower())
    if match.group("roman"):
        return ROMAN_TO_INT.get(match.group("roman").upper())
    if match.group("arabic"):
        return ARABIC_TO_INT.get(match.group("arabic"))
    if match.group("standalone_digit"):
        return ARABIC_TO_INT.get(match.group("standalone_digit"))

    return None


def detect_intent(query: str) -> str:
    """Detect question intent category."""
    if INTENT_CREDIT_INFO.search(query):
        return "credit_info"
    if INTENT_LIST_COURSES.search(query):
        return "list_courses"
    if INTENT_UNIT.search(query):
        return "unit"
    if INTENT_OBJECTIVES.search(query):
        return "objectives"
    if INTENT_OUTCOMES.search(query):
        return "outcomes"
    if INTENT_COURSE_DETAIL.search(query):
        return "course_detail"
    return "general"


def normalize_query(query: str) -> Dict[str, Any]:
    """
    Clean query, extract semester integer, and identify intent.

    Returns:
        {
            "cleaned_query": str,
            "search_query": str,
            "semester": int | None,
            "intent": str,
            "where": dict | None,
        }
    """
    semester = extract_semester(query)
    intent = detect_intent(query)

    # Strip conversational filler words
    cleaned = FILLER_PATTERNS.sub("", query)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if semester:
        # Standardize semester mention for search vector
        search_query = SEM_REGEX.sub(f"semester {semester} courses", cleaned, count=1)
        where = {"semester": semester}
    else:
        search_query = cleaned
        where = None

    return {
        "cleaned_query": cleaned,
        "search_query": search_query.strip(),
        "semester": semester,
        "intent": intent,
        "where": where,
    }
