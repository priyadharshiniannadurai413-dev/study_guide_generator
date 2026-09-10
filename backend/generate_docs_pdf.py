"""
generate_docs_pdf.py
--------------------
Generates a comprehensive academic and architectural specification PDF
for the AI Study Assistant project export.
"""

import os
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_project_docs_pdf(output_filename: str = "AI_Study_Assistant_Project_Docs.pdf") -> str:
    """Generate a clean, structured documentation PDF for the AI Study Assistant."""
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,  # Center
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#64748b"),
        alignment=1,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=4,
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("AI Study Assistant", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Comprehensive Architecture & Subsystem Specification", subtitle_style))
    story.append(Paragraph(f"Exported: {datetime.now(timezone.utc).strftime('%B %d, %Y')} | Engineering Release", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=14))

    # Executive Summary
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(Paragraph(
        "The AI Study Assistant is an intelligent, multi-model university curriculum and learning assistant. "
        "It integrates structure-aware document parsing, dense vector similarity search with Reciprocal Rank Fusion (RRF), "
        "multi-tenant PDF ingestion, dedicated study material generation (summaries & 4-option MCQs), "
        "real-time Server-Sent Events (SSE) chat streaming, voice input/output, and GitHub Copilot MCP connectivity.",
        body_style,
    ))

    # Architecture Overview Table
    story.append(Paragraph("2. System Architecture & Components", h1_style))
    arch_data = [
        ["Subsystem", "Technologies", "Description"],
        ["API Core", "FastAPI, Uvicorn, Pydantic v2", "High-performance async REST API with CORS and SSE streaming"],
        ["Auth Layer", "Clerk JWT, JWKS, Fernet", "Bearer token verification & AES-CBC token encryption at rest"],
        ["Syllabus RAG", "LangChain, MongoDB Atlas, Gemini", "Hybrid vector + keyword search with RRF for global syllabus"],
        ["User Documents", "pdfplumber, Motor, isolated coll", "Tenant-scoped PDF upload and retrieval partitioned by user_id"],
        ["Study Engine", "Gemini 3.5 Flash, Pydantic", "Structured StudyNotes & QuizDeck (4 options with explanations)"],
        ["AI Core", "LiteLLM, Mistral Small, Gemini Flash", "Multi-round tool loop (4 rounds) with model failover"],
        ["MCP Integration", "GitHub MCP, SSE, OAuth", "GitHub repository, PR, and issue actions (32 essential tools)"],
        ["Voice I/O", "Groq Whisper, Edge-TTS", "Audio transcription and real-time MP3 speech synthesis"],
    ]

    arch_table = Table(arch_data, colWidths=[110, 160, 250])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 12))

    # Database Schema
    story.append(Paragraph("3. Database Collections & Indexing", h1_style))
    db_text = (
        "MongoDB stores all application data partitioned cleanly across three isolated collections:<br/>"
        "• <b>vector_documents</b>: Global university syllabus chunks and 384-dimensional embeddings with text & vector indexes.<br/>"
        "• <b>user_documents</b>: Student uploaded PDFs (lecture notes, question banks). Strictly filtered by compound index on "
        "<code>{'user_id': 1, 'doc_id': 1}</code>. Student uploads never pollute the college syllabus.<br/>"
        "• <b>github_tokens</b>: User GitHub OAuth access tokens encrypted at rest via Fernet with <code>TOKEN_ENCRYPTION_KEY</code>."
    )
    story.append(Paragraph(db_text, body_style))

    # REST API Catalog Table
    story.append(Paragraph("4. Core API Endpoints Catalog", h1_style))
    api_data = [
        ["Method", "Endpoint", "Auth", "Description"],
        ["GET", "/health", "None", "System health check"],
        ["POST", "/api/chat/stream", "Clerk JWT", "Server-Sent Events real-time token streaming"],
        ["POST", "/api/documents/upload", "Clerk JWT", "Upload and ingest PDF (max 25MB)"],
        ["GET", "/api/documents/", "Clerk JWT", "List user's uploaded documents catalog"],
        ["DELETE", "/api/documents/{doc_id}", "Clerk JWT", "Delete document chunks belonging to user"],
        ["POST", "/api/study/notes", "Clerk JWT", "Generate structured high-yield revision notes"],
        ["POST", "/api/study/mcq", "Clerk JWT", "Generate 4-option MCQs with explanations"],
        ["POST", "/api/voice/transcribe", "None/Clerk", "Speech-to-Text via Groq Whisper"],
        ["POST", "/api/voice/synthesize", "None/Clerk", "Text-to-Speech MP3 stream via Edge TTS"],
        ["GET", "/auth/github/url", "Clerk JWT", "Generate secure GitHub OAuth authorization URL"],
        ["GET", "/auth/github/callback", "None", "OAuth code exchange and encrypted token persistence"],
    ]

    api_table = Table(api_data, colWidths=[55, 140, 65, 260])
    api_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(api_table)
    story.append(Spacer(1, 12))

    # Security & Guardrails
    story.append(Paragraph("5. Security & Isolation Guarantees", h1_style))
    story.append(Paragraph(
        "• <b>Zero Tenant Leakage</b>: All user queries, study generation requests, and deletions strictly require "
        "the authenticated user's ID (Clerk 'sub'). Defense-in-depth filters reject mismatched cross-user operations.<br/>"
        "• <b>Credential Protection</b>: GitHub OAuth tokens are encrypted using AES-128 in CBC mode (Fernet) before MongoDB write. "
        "Plaintext tokens are never logged or returned in HTTP responses.<br/>"
        "• <b>Safe Fallback Execution</b>: Model failovers automatically switch from Mistral Small to Gemini 1.5 Flash on "
        "rate limits or API errors. MCP tool errors are caught and summarized without halting the chat stream.",
        body_style,
    ))

    # Build PDF
    doc.build(story)
    print(f"✅ Generated project documentation PDF: {output_filename}")
    return output_filename


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "AI_Study_Assistant_Project_Docs.pdf"
    build_project_docs_pdf(out_file)
