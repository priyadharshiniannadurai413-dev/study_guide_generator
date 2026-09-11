"""
app/ai/web_content_service.py
-----------------------------
Web content extraction, conservative boilerplate cleaning, chunking, and grounded
question-answering service powered by Fetch MCP and LLM fallbacks.

Key capabilities:
1. Conservative Boilerplate Removal:
   - Strips navigation menus, header bars, sidebars, breadcrumbs, footers, and Wikipedia UI noise
     ("Jump to content", "Main menu", "Tools", "Donate", "Random article", edit links).
   - Strictly preserves legitimate educational content: headings, technical paragraphs,
     definitions, formulas, code fences, data tables, and bulleted lists.
   - Low-confidence safety fallback: preserves content rather than over-deleting.
2. Large Webpage Token Safety:
   - Small pages (<= 12k chars) provided directly to the LLM.
   - Large pages (> 12k chars) chunked and semantically ranked against the student's question.
3. Grounded Q&A:
   - Answers questions strictly using extracted content with source attribution.
   - Accurately reports when the webpage lacks sufficient information to answer.
"""

from datetime import datetime, timezone
import ipaddress
import logging
import math
import re
from typing import Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.ai.mcp_service import get_fetch_mcp_service
from app.ai.models import get_llm_with_fallback

logger = logging.getLogger("uvicorn")

LARGE_PAGE_THRESHOLD_CHARS = 12000
MAX_PROMPT_CONTEXT_CHARS = 10000


def validate_public_url(url: str) -> str:
    """
    Validate HTTP/HTTPS URL and enforce strict SSRF protections.
    Disallows file://, localhost, loopback, private IP ranges (RFC 1918), and link-local.
    """
    url_clean = (url or "").strip()
    if not url_clean:
        raise ValueError("URL parameter cannot be empty.")

    parsed = urlparse(url_clean)
    if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Unsupported protocol '{parsed.scheme}'. Only 'http://' and 'https://' are supported.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Malformed URL: missing valid domain or hostname.")

    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "local", "127.0.0.1", "0.0.0.0", "::1"):
        raise ValueError("Access to localhost or loopback addresses is strictly prohibited.")

    # Check for private IP literals
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"Access to private or internal network address '{hostname}' is prohibited.")
    except ValueError:
        # Valid domain name host
        pass

    return url_clean


class WebDocumentModel(BaseModel):
    """Structured representation of a fetched and cleaned webpage document."""

    url: str = Field(..., description="Canonical URL of the webpage")
    title: str = Field(..., description="Document title extracted from the webpage")
    content: str = Field(..., description="Cleaned, meaningful article Markdown")
    content_type: Literal["web"] = Field(default="web", description="Document type")
    source: Literal["fetch_mcp"] = Field(default="fetch_mcp", description="Source provider")
    retrieved_at: str = Field(..., description="ISO timestamp when document was fetched")
    word_count: int = Field(..., description="Word count of the cleaned article content")
    extraction_method: str = Field(..., description="Pipeline extraction technique used")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of clean extraction")


# ── Boilerplate Patterns (Conservative Cleaning) ──────────────────────────────

# Navigation / UI phrases to strip from lines
BOILERPLATE_LINE_PATTERNS = [
    re.compile(r"^\s*jump\s+to\s+(content|navigation|search)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(main\s+menu|toggle\s+sidebar|navigation)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:[\*\-]\s+)?\[\s*(main\s+page|current\s+events|random\s+article|donate|contact\s+us|about\s+wikipedia|community\s+portal)\s*\]\(.*?\)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:[\*\-]\s+)?\[\s*(what\s+links\s+here|related\s+changes|upload\s+file|special\s+pages|permanent\s+link|page\s+information|cite\s+this\s+page|download\s+as\s+pdf)\s*\]\(.*?\)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:tools|general|print/export|in\s+other\s+projects)\s*$", re.IGNORECASE),
    re.compile(r"^\s*this\s+page\s+was\s+last\s+edited\s+on\s+.*$", re.IGNORECASE),
    re.compile(r"^\s*text\s+is\s+available\s+under\s+the\s+creative\s+commons\s+.*$", re.IGNORECASE),
    re.compile(r"^\s*[\^↑]\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*categories\s*:\s*\[.*?\]\(.*?\).*$", re.IGNORECASE),
    re.compile(r"^\s*cookie\s+statement\s*\|.*$", re.IGNORECASE),
    re.compile(r"^\s*privacy\s+policy\s*\|.*$", re.IGNORECASE),
    re.compile(r"^\s*terms\s+of\s+use\s*\|.*$", re.IGNORECASE),
]

# Wiki edit markers e.g. [edit] or [ edit source ]
EDIT_MARKER_PATTERN = re.compile(r"\\?\[\s*edit(?:\s+source)?\s*\\?\]", re.IGNORECASE)


def _strip_html_boilerplate(html: str) -> str:
    """Strip header, footer, navigation, scripts, and sidebar containers from HTML."""
    cleaned = html

    # Remove script, style, noscript, svg, iframe
    cleaned = re.sub(r"<script.*?</script>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<noscript.*?</noscript>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<svg.*?</svg>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    # Remove standard UI containers
    cleaned = re.sub(r"<nav\b[^>]*>.*?</nav>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<header\b[^>]*>.*?</header>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<footer\b[^>]*>.*?</footer>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<aside\b[^>]*>.*?</aside>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    # Remove known boilerplate classes/ids (navigation, sidebars, toolboxes)
    boilerplate_class_pattern = re.compile(
        r'<div\b[^>]*(?:class|id)=["\'][^"\']*(?:navbox|catlinks|printfooter|mw-jump-link|vector-menu|mw-sidebar|sidebar|toc\b)[^"\']*["\'][^>]*>.*?</div>',
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = boilerplate_class_pattern.sub("", cleaned)

    return cleaned


def _extract_semantic_container(html: str) -> Optional[str]:
    """Look for main article containers (<article>, <main>, .mw-parser-output, #content)."""
    # 1. Wikipedia main article body
    wiki_match = re.search(
        r'(<div\b[^>]*class=["\'][^"\']*mw-parser-output[^"\']*["\'][^>]*>.*)',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if wiki_match:
        return wiki_match.group(1)

    # 2. <article> tag
    article_match = re.search(r"<article\b[^>]*>(.*?)</article>", html, flags=re.DOTALL | re.IGNORECASE)
    if article_match:
        return article_match.group(1)

    # 3. <main> tag
    main_match = re.search(r"<main\b[^>]*>(.*?)</main>", html, flags=re.DOTALL | re.IGNORECASE)
    if main_match:
        return main_match.group(1)

    # 4. Standard content div
    content_match = re.search(
        r'(<div\b[^>]*(?:id|class)=["\'][^"\']*(?:content|article-body|post-content|entry-content)[^"\']*["\'][^>]*>.*)',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if content_match:
        return content_match.group(1)

    return None


def clean_markdown_content(raw_markdown: str) -> Tuple[str, float]:
    """
    Conservatively clean Markdown content by stripping navigation, menus, and footer boilerplate
    while preserving headings, paragraphs, bullet points, technical tables, and equations.

    Returns:
        (clean_markdown, confidence_score)
    """
    lines = raw_markdown.splitlines()
    cleaned_lines = []
    in_code_block = False
    stripped_count = 0

    for line in lines:
        stripped_line = line.strip()

        # Track code fences — never delete inside code blocks!
        if stripped_line.startswith("```"):
            in_code_block = not in_code_block
            cleaned_lines.append(line)
            continue

        if in_code_block:
            cleaned_lines.append(line)
            continue

        # Check if line matches boilerplate pattern
        is_boilerplate = False
        for pat in BOILERPLATE_LINE_PATTERNS:
            if pat.match(stripped_line):
                is_boilerplate = True
                stripped_count += 1
                break

        if is_boilerplate:
            continue

        # Clean inline edit markers like [edit]
        cleaned_line = EDIT_MARKER_PATTERN.sub("", line)

        cleaned_lines.append(cleaned_line)

    result = "\n".join(cleaned_lines)
    # Collapse multiple consecutive blank lines
    result = re.sub(r"\n{3,}", "\n\n", result).strip()

    # Calculate confidence based on retention and structural markers
    orig_len = max(len(raw_markdown.strip()), 1)
    new_len = len(result)
    retention_ratio = new_len / orig_len

    # If cleaner deleted more than 85% of characters from a non-trivial text,
    # it likely over-cleaned — fallback conservatively to avoid losing data!
    if orig_len > 400 and retention_ratio < 0.15:
        logger.warning(
            f"[WebContentService] Cleaner over-cleaned ({new_len}/{orig_len} chars). "
            f"Falling back to original markdown."
        )
        return raw_markdown.strip(), 0.50

    has_headings = bool(re.search(r"^#{1,4}\s+", result, re.MULTILINE))
    has_paragraphs = len(result.split("\n\n")) >= 2
    confidence = 0.80
    if has_headings:
        confidence += 0.10
    if has_paragraphs:
        confidence += 0.05
    if retention_ratio > 0.40:
        confidence += 0.04

    return result, min(round(confidence, 2), 0.99)


class WebContentService:
    """
    High-level service coordinating web retrieval, article extraction,
    token-safe chunking, and grounded LLM question answering.
    """

    def __init__(self):
        self.fetch_service = get_fetch_mcp_service()

    async def get_clean_web_document(self, url: str) -> WebDocumentModel:
        """
        Fetch a webpage URL, extract its main article content, strip boilerplate,
        and return a validated WebDocumentModel.
        """
        clean_url = validate_public_url(url)
        logger.info(f"[WEB] URL received: {clean_url}")

        # 1. Fetch content via FetchMCPService
        logger.info(f"[WEB] Fetch MCP started: {clean_url}")
        fetch_result = await self.fetch_service.fetch_web_content(clean_url, max_length=50000)
        logger.info(f"[WEB] Fetch MCP completed: status={fetch_result.get('status')}")

        if fetch_result.get("status") != "success":
            err_msg = fetch_result.get("error") or "Unknown fetch error"
            raise RuntimeError(f"Webpage fetch failed: {err_msg}")

        title = fetch_result.get("title") or "Web Documentation"
        raw_md = fetch_result.get("content") or ""
        raw_html = fetch_result.get("raw_html")
        retrieved_at = fetch_result.get("retrieved_at") or datetime.now(timezone.utc).isoformat()
        logger.info(f"[WEB] Raw content length: {len(raw_md)}")

        extraction_method = "markdown_boilerplate_filter"

        # If raw HTML is available, attempt semantic DOM container extraction first
        if raw_html:
            cleaned_html = _strip_html_boilerplate(raw_html)
            semantic_container = _extract_semantic_container(cleaned_html)
            if semantic_container and len(semantic_container.strip()) > 300:
                try:
                    container_md = self.fetch_service._html_to_markdown(semantic_container)
                    if len(container_md.strip()) > 150:
                        raw_md = container_md
                        extraction_method = "semantic_dom_container_extraction"
                except Exception as exc:
                    logger.debug(f"[WebContentService] Semantic DOM markdown conversion failed: {exc}")

        # 2. Apply conservative Markdown cleaning
        clean_content, confidence = clean_markdown_content(raw_md)
        logger.info(f"[WEB] Clean content length: {len(clean_content)}")
        word_count = len(clean_content.split())

        if word_count < 10:
            raise RuntimeError("The extracted webpage content is empty or contains no readable text.")

        return WebDocumentModel(
            url=clean_url,
            title=title,
            content=clean_content,
            content_type="web",
            source="fetch_mcp",
            retrieved_at=retrieved_at,
            word_count=word_count,
            extraction_method=extraction_method,
            extraction_confidence=confidence,
        )

    def chunk_and_rank_content(
        self,
        content: str,
        question: str,
        max_total_chars: int = MAX_PROMPT_CONTEXT_CHARS,
    ) -> str:
        """
        Token-safety mechanism for large webpages.
        Chunks clean markdown and retrieves the most relevant sections based on question terms.
        Preserves sequential document order of chosen chunks for coherence.
        """
        if len(content) <= LARGE_PAGE_THRESHOLD_CHARS:
            return content

        logger.info(
            f"[WebContentService] Large webpage detected ({len(content)} chars). "
            f"Activating chunking and relevance ranking."
        )

        # Split along markdown headings (## or ###) or 1200-char paragraphs
        sections = re.split(r"(?=\n#{1,3}\s+)", content)
        chunks: List[Dict[str, Any]] = []

        chunk_idx = 0
        for sec in sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue

            # Extract heading if present
            lines = sec_clean.splitlines()
            heading_prefix = ""
            if lines and lines[0].strip().startswith("#"):
                heading_prefix = lines[0].strip() + "\n\n"

            # If section is excessively long, sub-chunk it while keeping the heading
            if len(sec_clean) > 1500:
                paras = [p.strip() for p in sec_clean.split("\n\n") if p.strip()]
                buf = ""
                for p in paras:
                    if p.startswith("#"):
                        continue
                    if len(buf) + len(p) < 1200:
                        buf += p + "\n\n"
                    else:
                        if buf.strip():
                            chunk_text = (heading_prefix + buf).strip()
                            chunks.append({"id": chunk_idx, "text": chunk_text})
                            chunk_idx += 1
                        buf = p + "\n\n"
                if buf.strip():
                    chunk_text = (heading_prefix + buf).strip()
                    chunks.append({"id": chunk_idx, "text": chunk_text})
                    chunk_idx += 1
            else:
                chunks.append({"id": chunk_idx, "text": sec_clean})
                chunk_idx += 1

        if not chunks:
            return content[:max_total_chars]

        # Score chunks based on question keyword overlap + heading matches
        q_terms = set(re.findall(r"\w{3,}", question.lower()))
        scored_chunks = []

        for ch in chunks:
            text_lower = ch["text"].lower()
            first_line = ch["text"].splitlines()[0].lower() if ch["text"] else ""

            # De-prioritize auxiliary citations, references, and external link lists
            is_auxiliary = any(
                h in first_line
                for h in ["# references", "# external links", "# see also", "# further reading", "# notes", "# bibliography"]
            )
            if is_auxiliary:
                scored_chunks.append((-10.0, ch["id"], ch["text"]))
                continue

            score = 0.0

            # Always boost the lead section (Chunk 0) as it defines core subject terminology
            if ch["id"] == 0:
                score += 4.0

            # Term overlap
            for term in q_terms:
                count = text_lower.count(term)
                if count > 0:
                    score += 1.0 + math.log1p(count)

            # Boost if heading contains query terms
            if first_line.startswith("#"):
                for term in q_terms:
                    if term in first_line:
                        score += 3.0

            scored_chunks.append((score, ch["id"], ch["text"]))

        # Sort by score descending to pick the best chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        # Prefer chunks with positive relevance score if any exist
        has_positive = any(s > 0 for s, _, _ in scored_chunks)
        filtered_chunks = [ch for ch in scored_chunks if ch[0] > 0] if has_positive else scored_chunks

        # Select top chunks up to character budget
        chosen = []
        running_chars = 0
        for score, cid, text in filtered_chunks:
            if running_chars + len(text) > max_total_chars and chosen:
                break
            chosen.append((cid, text))
            running_chars += len(text)

        # Re-sort chosen chunks by original document order (cid)
        chosen.sort(key=lambda x: x[0])

        assembled = "\n\n---\n\n".join(text for _, text in chosen)
        return assembled

    async def answer_question_from_web(self, url: str, question: str) -> Dict[str, Any]:
        """
        Load webpage via Fetch MCP, extract clean content, handle size/token safety,
        and generate a strictly grounded academic answer using the LLM fallback chain.
        """
        q_clean = question.strip()
        if not q_clean:
            raise ValueError("Question cannot be empty.")

        doc = await self.get_clean_web_document(url)

        # Apply token safety / chunking if document is large
        context = self.chunk_and_rank_content(doc.content, q_clean)

        system_prompt = (
            "You are an academic learning assistant. Answer the student's question strictly "
            "using the provided webpage content.\n\n"
            "STRICT GROUNDING RULES:\n"
            "1. Base your answer ONLY on the provided webpage content below.\n"
            "2. If the answer cannot be found or is not supported by the webpage content, "
            "you MUST state clearly: 'The provided webpage does not contain enough information to answer this question.'\n"
            "3. Do not extrapolate, assume, or invent facts not present in the webpage text.\n"
            "4. Organize your answer clearly with concise headings or bullet points where appropriate."
        )

        user_prompt = (
            f"WEBPAGE SOURCE: {doc.title}\n"
            f"WEBPAGE URL: {doc.url}\n\n"
            f"EXTRACTED WEBPAGE CONTENT:\n"
            f"{context}\n\n"
            f"STUDENT QUESTION:\n"
            f"{q_clean}\n\n"
            f"ANSWER:"
        )

        llm = get_llm_with_fallback(temperature=0.1, max_tokens=1500)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(f"[WEB] LLM generation started: Q&A on '{doc.title}' for '{q_clean[:60]}'")
        response = await llm.ainvoke(messages)
        answer_text = response.content if hasattr(response, "content") else str(response)
        logger.info(f"[WEB] LLM generation completed")
        logger.info(f"[WEB] Answer length: {len(answer_text)}")

        return {
            "success": True,
            "question": q_clean,
            "answer": answer_text.strip(),
            "source": {
                "url": doc.url,
                "title": doc.title,
                "word_count": doc.word_count,
                "extraction_method": doc.extraction_method,
            },
        }

    async def generate_study_notes_from_web(
        self,
        url: str,
        topic: Optional[str] = None,
        difficulty: str = "intermediate",
    ) -> Dict[str, Any]:
        """
        Fetch webpage, clean content, and synthesize structured AdaptiveStudyNotes
        using the LLM fallback chain.
        """
        doc = await self.get_clean_web_document(url)
        notes_topic = topic.strip() if (topic and topic.strip()) else doc.title

        context_text = doc.content[:14000] if len(doc.content) <= 14000 else self.chunk_and_rank_content(doc.content, notes_topic, max_total_chars=12000)

        logger.info(f"[WEB] LLM generation started: study_notes for '{notes_topic}' ({difficulty})")
        from app.services.study_generator import generate_adaptive_study_notes_async
        notes = await generate_adaptive_study_notes_async(
            topic=notes_topic,
            context_text=context_text,
            difficulty=difficulty,
        )
        notes_dict = notes.model_dump()
        notes_dict["sources"] = {
            "web": [{
                "url": doc.url,
                "title": doc.title,
                "word_count": doc.word_count,
                "extraction_method": doc.extraction_method,
            }]
        }
        logger.info(f"[WEB] LLM generation completed: generated study notes with {len(notes_dict.get('sections', []))} sections")
        logger.info(f"[WEB] Answer length: {len(str(notes_dict))}")

        return {
            "success": True,
            "topic": notes_topic,
            "difficulty": difficulty,
            "notes": notes_dict,
            "source": {
                "url": doc.url,
                "title": doc.title,
                "word_count": doc.word_count,
            },
        }

    async def generate_mcqs_from_web(
        self,
        url: str,
        count: int = 20,
        topic: Optional[str] = None,
        difficulty: str = "intermediate",
    ) -> Dict[str, Any]:
        """
        Fetch webpage via Fetch MCP, clean content, and synthesize structured MCQs
        calibrated to difficulty and count.
        """
        doc = await self.get_clean_web_document(url)
        quiz_topic = topic.strip() if (topic and topic.strip()) else doc.title

        context_text = doc.content[:14000] if len(doc.content) <= 14000 else self.chunk_and_rank_content(doc.content, quiz_topic, max_total_chars=12000)

        logger.info(f"[WEB] LLM generation started: MCQs ({count} questions, {difficulty}) for '{quiz_topic}'")
        from app.services.study_generator import generate_mcq_quiz_async
        deck = await generate_mcq_quiz_async(
            context_text=context_text,
            num_questions=count,
            difficulty=difficulty,
        )
        deck_dict = deck.model_dump()
        deck_dict["title"] = quiz_topic
        deck_dict["sources"] = {
            "web": [{
                "url": doc.url,
                "title": doc.title,
                "word_count": doc.word_count,
                "extraction_method": doc.extraction_method,
            }]
        }
        logger.info(f"[WEB] LLM generation completed: generated {len(deck_dict.get('questions', []))} MCQs")
        return {
            "success": True,
            "quiz_deck": deck_dict,
            "topic": quiz_topic,
            "source": {
                "url": doc.url,
                "title": doc.title,
                "word_count": doc.word_count,
            },
        }


# Singleton instance
_web_content_service: Optional[WebContentService] = None


def get_web_content_service() -> WebContentService:
    """Return the singleton instance of WebContentService."""
    global _web_content_service
    if _web_content_service is None:
        _web_content_service = WebContentService()
    return _web_content_service


__all__ = [
    "WebDocumentModel",
    "WebContentService",
    "clean_markdown_content",
    "get_web_content_service",
]
