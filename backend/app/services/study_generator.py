"""
app/services/study_generator.py
---------------------------------
Structured Study Guide & MCQ Generation Engine using Google Gemini and Pydantic schemas.
Enforces strict JSON schema validation via LangChain's structured output.
"""

import asyncio
import logging
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, model_validator

from app.core.config import settings
from app.ai.schemas import AdaptiveStudyNotes, TopicDetailBlock

logger = logging.getLogger("uvicorn")

# Default Gemini model verified to support structured output with high throughput
DEFAULT_STUDY_GEN_MODEL = "gemini-3.5-flash-lite"

CANDIDATE_STUDY_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
]

DifficultyLevel = Literal["beginner", "intermediate", "advanced"]


def get_difficulty_notes_prompt(difficulty: DifficultyLevel) -> str:
    """Generate prompt instructions calibrating depth, vocabulary, and concepts for study notes."""
    if difficulty == "beginner":
        return (
            "CALIBRATION LEVEL - BEGINNER:\n"
            "- Depth: Foundational and conceptual introduction.\n"
            "- Vocabulary: Accessible, clear, avoiding unexplained jargon or dense mathematical proofs.\n"
            "- Explanation style: Intuitive analogies, step-by-step breakdowns, and practical everyday analogies.\n"
            "- Focus: Defining what the concept is, why it matters, basic declarations/syntax, and core purpose."
        )
    elif difficulty == "advanced":
        return (
            "CALIBRATION LEVEL - ADVANCED:\n"
            "- Depth: Deep theoretical rigor, low-level internal mechanics, architectural analysis, and mathematical formalisms.\n"
            "- Vocabulary: High-density domain terminology, formal academic and systems engineering lexicon.\n"
            "- Explanation style: Thorough exploration of subtle edge cases, concurrency/memory constraints, non-obvious failure modes, and performance trade-offs.\n"
            "- Focus: Multi-step derivations, internal implementation details, and architectural critique."
        )
    else:  # intermediate (default)
        return (
            "CALIBRATION LEVEL - INTERMEDIATE:\n"
            "- Depth: Balanced operational mechanics and standard university undergraduate curriculum depth.\n"
            "- Vocabulary: Standard professional and engineering terminology with clear technical definitions.\n"
            "- Explanation style: Real-world engineering patterns, standard algorithmic workflows, and practical code/diagram structures.\n"
            "- Focus: How components operate, interact, and practical trade-offs encountered in real-world application."
        )


def get_difficulty_mcq_prompt(difficulty: DifficultyLevel) -> str:
    """Generate prompt instructions calibrating depth, vocabulary, and distractor plausibility for MCQs."""
    if difficulty == "beginner":
        return (
            "CALIBRATION LEVEL - BEGINNER:\n"
            "- Question Depth: Foundational recall, basic definitions, primary components, and direct identification.\n"
            "- Vocabulary: Clear, simple, and direct language without ambiguous phrasing.\n"
            "- Distractors: Distinct and clearly incorrect to someone who knows the basics, avoiding tricky fine-grained distinctions.\n"
            "- Explanations: Clear, educational, step-by-step explanations reinforcing foundational concepts."
        )
    elif difficulty == "advanced":
        return (
            "CALIBRATION LEVEL - ADVANCED:\n"
            "- Question Depth: Multi-step reasoning, complex scenario analysis, subtle edge cases, architectural trade-offs, and failure mode diagnosis.\n"
            "- Vocabulary: Rigorous academic and professional engineering terminology.\n"
            "- Distractors: Highly plausible, sophisticated distractors representing deep, non-trivial misconceptions and subtle technical traps.\n"
            "- Explanations: In-depth technical justifications dissecting why the correct option is optimal and why each specific distractor fails."
        )
    else:  # intermediate (default)
        return (
            "CALIBRATION LEVEL - INTERMEDIATE:\n"
            "- Question Depth: Application-oriented reasoning, code tracing, operational behavior, and architectural comparison.\n"
            "- Vocabulary: Standard technical and university-level engineering terminology.\n"
            "- Distractors: Plausible options reflecting common student misunderstandings, implementation pitfalls, or typical bugs.\n"
            "- Explanations: Comprehensive conceptual explanations detailing operational principles and mechanics."
        )


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class MCQItem(BaseModel):
    """A single multiple choice question with 4 options and conceptual explanation."""

    question: str = Field(description="The question prompt")
    options: List[str] = Field(description="Exactly 4 distinct choices")
    correct_answer: str = Field(default="", description="The verbatim text of the correct choice")
    explanation: str = Field(description="Detailed conceptual explanation of why the answer is correct")
    correct_index: Optional[int] = Field(default=None, description="Index (0-3) of the correct answer")
    reference_page: Optional[int] = Field(default=None, description="Source page number")

    @model_validator(mode="after")
    def sync_correct_fields(self) -> "MCQItem":
        if not self.correct_answer and self.correct_index is not None and self.options:
            if 0 <= self.correct_index < len(self.options):
                self.correct_answer = self.options[self.correct_index]
        elif self.correct_answer and self.correct_index is None and self.options:
            for idx, opt in enumerate(self.options):
                if opt.strip().lower() == self.correct_answer.strip().lower():
                    self.correct_index = idx
                    break
            if self.correct_index is None:
                self.correct_index = 0
        return self


class ShortAnswerItem(BaseModel):
    """Conceptual or analytical short-answer question with exemplar answer and grading rubric."""

    question: str = Field(description="Conceptual or analytical question")
    model_answer: str = Field(description="Comprehensive exemplar answer covering key points")
    grading_criteria: List[str] = Field(description="Key concepts or keywords required for full marks")


class GlossaryItem(BaseModel):
    """Key terms glossary entry."""

    term: str = Field(description="Core technical term or concept")
    definition: str = Field(description="Concise, precise academic definition")


class CompleteStudyPack(BaseModel):
    """Complete multi-part academic study pack calibrated to target difficulty."""

    title: str = Field(description="Subject title or lecture topic")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="intermediate",
        description="Target difficulty level of questions and depth",
    )
    concise_summary: str = Field(description="Dense, structured summary notes of the material")
    suggested_study_order: List[str] = Field(description="Step-by-step recommended study progression")
    glossary: List[GlossaryItem] = Field(description="Key terms glossary")
    mcqs: List[MCQItem] = Field(description="Exactly 20 practice MCQs calibrated to the selected difficulty")
    short_answers: List[ShortAnswerItem] = Field(description="Exactly 5 short-answer questions with model answers")


class QuizDeck(BaseModel):
    """Collection of multiple choice questions forming an academic quiz."""

    title: str = Field(description="Quiz topic or title")
    questions: List[MCQItem] = Field(description="List of generated MCQs")


class ConceptBlock(BaseModel):
    """A granular technical concept with explanation, exact syntax/formula, and practical application."""

    subtopic: str = Field(description="Subtopic or core concept name")
    explanation: str = Field(description="Intuitive, in-depth explanation of how it works")
    syntax_or_formula: Optional[str] = Field(default=None, description="Exact code syntax, algorithm logic, or mathematical formula")
    practical_example: Optional[str] = Field(default=None, description="Short code snippet or practical application demonstrating the concept")


class TopicStudyNotes(BaseModel):
    """Structured, student-friendly study notes tailored to a specific topic."""

    topic_title: str = Field(description="Main subject or topic title")
    quick_summary: str = Field(description="2-3 dense paragraphs explaining the 'What, Why, and How'")
    key_takeaways: List[str] = Field(description="Bulleted high-yield facts and revision points")
    concepts: List[ConceptBlock] = Field(description="Detailed conceptual breakdown of sub-concepts")
    common_pitfalls: List[str] = Field(description="Common mistakes, edge cases, and exam traps")
    external_references: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="External documentation or web references fetched via Fetch MCP",
    )

    def to_study_notes(self) -> "StudyNotes":
        """Convert to legacy StudyNotes schema."""
        return StudyNotes(
            topic_title=self.topic_title,
            executive_summary=self.quick_summary,
            core_concepts=[
                ConceptDefinition(
                    term=c.subtopic,
                    definition=c.explanation,
                    syntax_or_example=c.syntax_or_formula or c.practical_example,
                )
                for c in self.concepts
            ],
            syntax_and_formulas=[c.syntax_or_formula for c in self.concepts if c.syntax_or_formula],
            high_yield_revision_points=list(self.key_takeaways) + list(self.common_pitfalls),
        )

    def to_adaptive_study_notes(self) -> AdaptiveStudyNotes:
        """Convert TopicStudyNotes to AdaptiveStudyNotes."""
        return AdaptiveStudyNotes(
            title=self.topic_title,
            executive_summary=self.quick_summary,
            sections=[
                TopicDetailBlock(
                    title=c.subtopic,
                    overview=c.explanation,
                    key_points=[c.practical_example] if c.practical_example else [],
                    code_or_syntax=c.syntax_or_formula,
                )
                for c in self.concepts
            ],
            actionable_takeaways=list(self.key_takeaways) + list(self.common_pitfalls),
        )


class ConceptDefinition(BaseModel):
    """Deep technical concept definition with operational mechanics and code/formula example."""

    term: str = Field(description="Technical concept, keyword, or construct name")
    definition: str = Field(description="In-depth explanation of operational mechanics and behavior")
    syntax_or_example: Optional[str] = Field(
        default=None,
        description="Markdown code snippet, syntax pattern, or formula illustrating usage",
    )


class StudyNotes(BaseModel):
    """High-yield structured study notes for academic revision and exam preparation."""

    topic_title: str = Field(default="Study Guide", description="Specific technical topic or domain covered")
    executive_summary: str = Field(
        description="2-3 dense academic paragraphs explaining core principles, engineering mechanics, and applications"
    )
    core_concepts: List[ConceptDefinition] = Field(
        default_factory=list,
        description="Exhaustive list of core concepts, constructs, and keywords"
    )
    syntax_and_formulas: List[str] = Field(
        default_factory=list,
        description="Essential syntax rules, mathematical formulas in LaTeX, or code idioms"
    )
    high_yield_revision_points: List[str] = Field(
        default_factory=list,
        description="High-yield exam takeaways: edge cases, common pitfalls, performance trade-offs, and critical rules"
    )

    # Backward-compatible fields
    key_concepts: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Backward-compatible list of concept -> definition dictionaries"
    )
    formulas_and_theorems: Optional[List[str]] = Field(
        default=None,
        description="Backward-compatible list of formulas/theorems"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "core_concepts" not in data and "key_concepts" in data:
                raw_kc = data.get("key_concepts") or []
                converted = []
                for item in raw_kc:
                    if isinstance(item, dict):
                        term = item.get("term") or item.get("concept") or next(iter(item.keys()), "Concept")
                        definition = item.get("definition") or next(iter(item.values()), "")
                        converted.append({"term": str(term), "definition": str(definition), "syntax_or_example": None})
                data["core_concepts"] = converted

            if "syntax_and_formulas" not in data and "formulas_and_theorems" in data:
                data["syntax_and_formulas"] = data.get("formulas_and_theorems") or []

        return data

    @model_validator(mode="after")
    def sync_compatibility_fields(self) -> "StudyNotes":
        if not self.key_concepts and self.core_concepts:
            self.key_concepts = [
                {"concept": c.term, "definition": c.definition}
                for c in self.core_concepts
            ]
        if not self.formulas_and_theorems and self.syntax_and_formulas:
            self.formulas_and_theorems = list(self.syntax_and_formulas)
        return self

    def to_topic_study_notes(self) -> "TopicStudyNotes":
        """Convert legacy StudyNotes to TopicStudyNotes."""
        concepts = [
            ConceptBlock(
                subtopic=c.term,
                explanation=c.definition,
                syntax_or_formula=c.syntax_or_example,
                practical_example=None,
            )
            for c in self.core_concepts
        ]
        if not concepts:
            concepts = [
                ConceptBlock(
                    subtopic=self.topic_title,
                    explanation=self.executive_summary,
                    syntax_or_formula=self.syntax_and_formulas[0] if self.syntax_and_formulas else None,
                    practical_example=None,
                )
            ]
        takeaways = self.high_yield_revision_points[:5] if self.high_yield_revision_points else ["High-yield exam concept."]
        pitfalls = self.high_yield_revision_points[5:] if len(self.high_yield_revision_points) > 5 else ["Review syntax boundary conditions and common exam traps."]
        return TopicStudyNotes(
            topic_title=self.topic_title,
            quick_summary=self.executive_summary,
            key_takeaways=takeaways,
            concepts=concepts,
            common_pitfalls=pitfalls,
        )


STUDY_NOTES_SYSTEM_PROMPT = """You are an expert engineering professor and curriculum architect.
Your task is to transform technical texts into a comprehensive, high-yield Academic Study Guide.

DOCUMENT CATEGORY DETECTION & ADAPTATION:
Analyze the provided source context to detect its document category and adapt your extraction strategy accordingly:

1. CATEGORY A: TECHNICAL LECTURE / TEXTBOOK / CODE GUIDE:
   - Extract operational mechanics, control flow, underlying data structures, algorithms, and architectural principles.
   - For code-heavy topics, include concrete syntax rules, parameter behaviors, time/space complexity, and code idioms.
   - High-yield revision points must target tricky exam questions: common syntax errors, edge cases, gotchas, and distinctions between similar concepts.

2. CATEGORY B: COURSE SYLLABUS, PROJECT CATALOG, OR ASSIGNMENT SPECIFICATION:
   - DO NOT fabricate synthetic syntax rules or pretend it is a single programming chapter.
   - In executive_summary: Extract a Markdown Comparison Table of all Modules/Projects (Columns: Module / Project Title | Architecture / Focus | Tech Stack / Tools | Deliverables).
   - Detail the core engineering paradigms introduced across the curriculum or catalog.
   - In core_concepts: Detail each module, project milestone, or core paradigm (architectural layers, system workflows, and protocols). For syntax_or_example, supply stack configuration, CLI invocation, or architecture pattern (never invent fake language syntax).
   - In syntax_and_formulas: List required toolchains, tech stack dependencies, CLI workflows, or grading/complexity metrics.
   - In high_yield_revision_points: Formulate actionable high-yield checkpoints based on the evaluation criteria, submission requirements, grading weightage, and critical prerequisites.

CRITICAL CONTENT CONSTRAINTS:
1. STRICTLY EXCLUDE ADMINISTRATIVE & METADATA:
   - Completely ignore authors, publishers, ISBNs, licensing agreements (EULA), copyright pages, and affiliations.
   - Never output definitions or revision bullets concerning publishing rights, legal jurisdiction, or author bios.
2. ZERO HALLUCINATIONS:
   - Base all content strictly on the engineering substance and specifications provided in the context.
"""

STUDY_NOTES_USER_PROMPT = """Analyze the provided technical context and generate a complete StudyNotes payload following the required schema.

SOURCE CONTEXT:
---
{context_text}
---

INSTRUCTIONS:
1. Detect whether the input is a Technical Lecture/Textbook OR a Course Syllabus / Project Catalog / Assignment Specification.
2. If textbook/lecture: Extract deep mechanics, formulas, definitions, and code syntax.
3. If course syllabus/project catalog:
   - DO NOT fabricate synthetic syntax rules or pretend it is a single programming chapter.
   - Include a Markdown Comparison Table of all Modules/Projects in executive_summary.
   - Detail core engineering paradigms and architectures in core_concepts.
   - Formulate High-Yield Checkpoints based on evaluation criteria and submission requirements.
4. Remember: Zero mentions of authors, publishers, or licensing. Output only core engineering/academic substance."""


TOPIC_STUDY_NOTES_SYSTEM_PROMPT = """You are an elite academic professor, senior engineering educator, and curriculum architect.
Your task is to transform technical texts into structured, student-friendly, high-yield topic study notes.

DOCUMENT CATEGORY DETECTION & ADAPTATION:
Inspect the provided context and topic query to detect whether the material is a technical lecture/textbook or a course syllabus/project catalog/specification:

1. CATEGORY A: TECHNICAL LECTURE / TEXTBOOK / CODE GUIDE:
   - Explain 'What it is, Why it exists, and How it works mechanically'.
   - For every sub-concept:
     * Intuitive, in-depth technical explanation of operational mechanics.
     * Concrete syntax, algorithm pseudocode, or mathematical formula (in LaTeX or code blocks).
     * Practical code snippet or application demonstrating real-world usage.
   - Key takeaways: High-yield facts, performance characteristics, and rules for quick revision.
   - Common pitfalls: Actual student mistakes, syntax traps, boundary bugs, and anti-patterns.

2. CATEGORY B: COURSE SYLLABUS, PROJECT CATALOG, OR ASSIGNMENT SPECIFICATION:
   - DO NOT fabricate synthetic syntax rules or pretend it is a single programming chapter.
   - In quick_summary: Provide a clear academic overview, and include a Markdown Comparison Table of all Modules/Projects (Columns: Module / Project Title | Architecture / Focus | Tech Stack / Tools | Deliverables).
   - In concepts: Each ConceptBlock represents a module, project specification, or major engineering paradigm:
     * subtopic: Module / Project / Unit Title.
     * explanation: Architectural scope, engineering paradigms introduced, and technical objectives.
     * syntax_or_formula: Technology stack components, architecture flow, or CLI configuration (do NOT invent fake language syntax).
     * practical_example: Deliverables, project milestones, or implementation scenarios.
   - In key_takeaways: Formulate High-Yield Checkpoints based on the evaluation criteria, submission requirements, grading weightage, and critical prerequisites.
   - In common_pitfalls: Formulate pitfalls highlighting common submission traps, missing deliverables, scope creep, and evaluation penalties.

CRITICAL CONTENT CONSTRAINTS:
1. STRICTLY EXCLUDE ADMINISTRATIVE & METADATA:
   - Completely exclude authors, publishers, ISBNs, licensing agreements (EULA), copyright pages, and affiliations.
   - Never output definitions or revision bullets concerning publishing rights, legal jurisdiction, or author bios.
2. ZERO HALLUCINATIONS:
   - Strictly adhere to the technical substance in the provided source context.
"""

TOPIC_STUDY_NOTES_USER_PROMPT = """Analyze the provided context and generate a complete TopicStudyNotes payload for the topic: '{topic}'.

SOURCE CONTEXT:
---
{context_text}
---

INSTRUCTIONS:
1. Detect whether the input is a Technical Lecture/Textbook OR a Course Syllabus / Project Catalog / Assignment Specification.
2. If textbook/lecture: Focus on operational mechanics, concrete syntax/formulas, practical code examples, and student pitfalls.
3. If course syllabus/project catalog:
   - DO NOT fabricate synthetic syntax rules or pretend it is a single programming chapter.
   - In quick_summary, include a Markdown Comparison Table of all Modules/Projects (Title, Architecture, Tech Stack, Deliverables).
   - Detail the core engineering paradigms introduced in concepts.
   - Formulate High-Yield Checkpoints based on evaluation criteria and submission requirements in key_takeaways and common_pitfalls.
4. Remember: Zero mentions of authors, publishers, or licensing. Output only core engineering/academic substance."""


ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT = """You are an expert academic curriculum architect and senior engineering educator.
Your objective is to generate an exhaustive, comprehensive study guide that systematically covers the ENTIRE uploaded material without skipping sections.

CRITICAL INSTRUCTIONS FOR FULL COVERAGE:
1. COMPLETE ENUMERATION (ZERO OMISSIONS):
   - Walk through the material sequentially from the first page to the very last page.
   - If the document contains multiple projects (e.g., Projects 1 through 10), chapters, tracks, or modules, you MUST dedicate a distinct section in `sections` to EVERY single one.
   - Do NOT truncate, bundle into "etc.", summarize only a subset, or omit later units. Every project/module must have its own distinct TopicDetailBlock.
2. PRESERVE TECHNICAL DEPTH:
   - For every module or project, capture its core purpose, required components, architecture, and expected outputs in `overview` and `key_points`.
3. ADAPT TO DOCUMENT CONTENT:
   - If the material is a project list, syllabus, or project catalog: organize sections around project tracks, architectural patterns, tech stacks, and expected outputs. In executive_summary, provide a holistic synthesis and a Markdown Comparison Table listing ALL projects/modules (Columns: Title | Architecture / Focus | Tech Stack | Deliverables).
   - If the material is a technical lecture: organize around theory, operational mechanics, and definitions.
4. STRICTLY ELIMINATE ARTIFICIAL SYNTAX AND FORMULAS:
   - Do NOT invent programming syntax, library imports, or equations if the document does not center on them.
   - Never label library imports or tool configurations as "formulas".
   - If a section has no technical syntax or code, leave code_or_syntax as null.
5. REMOVE ADMINISTRATIVE PUBLISHING METADATA:
   - Do not include authors, affiliations, publishers, ISBNs, or licensing contracts.
   - Base all content strictly on the engineering substance provided in the context."""


ADAPTIVE_STUDY_NOTES_USER_PROMPT = """Analyze the provided context and generate an exhaustive AdaptiveStudyNotes payload for: '{topic}'.

SOURCE CONTEXT:
---
{context_text}
---

INSTRUCTIONS:
1. Systematically cover the entire context from page 1 to the final page.
2. If multiple projects, modules, or chapters are present, create a distinct section for EVERY single one without omitting or bundling any.
3. In executive_summary, provide a complete synthesis and a Markdown Comparison Table of all units.
4. Set 'code_or_syntax' ONLY if verbatim code/formula is explicitly in the text. Otherwise None.
5. Zero mentions of authors, publishers, or licensing."""


# ==============================================================================
# Helper LLM Factory
# ==============================================================================

def _get_llm(model_name: str = DEFAULT_STUDY_GEN_MODEL, temperature: Optional[float] = None) -> ChatGoogleGenerativeAI:
    """Instantiate and return a ChatGoogleGenerativeAI instance."""
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured in environment or settings. "
            "Please add GEMINI_API_KEY to your .env file."
        )
    kwargs: Dict[str, Any] = {
        "model": model_name,
        "google_api_key": api_key,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    return ChatGoogleGenerativeAI(**kwargs)


# ==============================================================================
# Multi-Provider Failovers (Groq & Mistral)
# ==============================================================================

def _generate_with_groq_topic_study_notes(topic: str, context_text: str) -> Optional[TopicStudyNotes]:
    """Failover generator for TopicStudyNotes using Groq's high-speed JSON inference."""
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return None
    try:
        import json
        from groq import Groq

        client = Groq(api_key=api_key)
        prompt = (
            f"{TOPIC_STUDY_NOTES_SYSTEM_PROMPT}\n\n"
            f"Generate topic study notes for '{topic}'. Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            f'  "topic_title": "{topic}",\n'
            '  "quick_summary": "2-3 dense paragraphs explaining the What, Why, and How",\n'
            '  "key_takeaways": ["Bulleted high-yield facts and revision points"],\n'
            '  "concepts": [\n'
            '    {\n'
            '      "subtopic": "Subtopic or core concept name",\n'
            '      "explanation": "Intuitive, in-depth explanation of how it works",\n'
            '      "syntax_or_formula": "Exact code syntax, algorithm logic, or mathematical formula or null",\n'
            '      "practical_example": "Short code snippet or practical application or null"\n'
            '    }\n'
            '  ],\n'
            '  "common_pitfalls": ["Common mistakes, edge cases, and exam traps"]\n'
            "}\n\n"
            f"--- CONTEXT START ---\n{context_text.strip()[:14000]}\n--- CONTEXT END ---\n\n"
            "Remember: Zero mentions of authors, publishers, or licensing. Output only core engineering/programming substance."
        )
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are an expert engineering professor. Respond ONLY with a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_json = resp.choices[0].message.content
        data = json.loads(raw_json)
        return TopicStudyNotes.model_validate(data)
    except Exception as exc:
        logger.warning(f"[GroqFailover] Groq topic study notes fallback failed: {exc}")
        return None


def _generate_with_mistral_topic_study_notes(topic: str, context_text: str) -> Optional[TopicStudyNotes]:
    """Failover generator for TopicStudyNotes using Mistral structured output."""
    api_key = getattr(settings, "MISTRAL_API_KEY", None)
    if not api_key:
        return None
    try:
        from langchain_mistralai import ChatMistralAI

        llm = ChatMistralAI(model="mistral-small-latest", api_key=api_key, temperature=0.2)
        structured_llm = llm.with_structured_output(TopicStudyNotes)
        system_prompt = TOPIC_STUDY_NOTES_SYSTEM_PROMPT
        human_prompt = TOPIC_STUDY_NOTES_USER_PROMPT.format(topic=topic, context_text=context_text.strip()[:14000])

        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        if isinstance(result, TopicStudyNotes):
            return result
        elif isinstance(result, dict):
            return TopicStudyNotes.model_validate(result)
    except Exception as exc:
        logger.warning(f"[MistralFailover] Mistral topic study notes fallback failed: {exc}")
        return None


def _generate_with_groq_adaptive_study_notes(
    topic: str,
    context_text: str,
    difficulty: DifficultyLevel = "intermediate",
) -> Optional[AdaptiveStudyNotes]:
    """Failover generator for AdaptiveStudyNotes using Groq's high-speed JSON inference."""
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return None
    try:
        import json
        from groq import Groq

        client = Groq(api_key=api_key)
        diff_instruction = get_difficulty_notes_prompt(difficulty)
        prompt = (
            f"{ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT}\n\n"
            f"{diff_instruction}\n\n"
            f"Generate adaptive study notes for '{topic}' at '{difficulty}' difficulty level. Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            f'  "title": "{topic}",\n'
            '  "executive_summary": "2-3 dense paragraphs synthesizing the core concepts, modules, and architecture",\n'
            '  "sections": [\n'
            '    {\n'
            '      "title": "Subtopic, module name, or project title",\n'
            '      "overview": "Clear explanation of the concept, purpose, or architecture",\n'
            '      "key_points": ["Concrete details, requirements, core principles, or components"],\n'
            '      "code_or_syntax": "Verbatim code snippet, mathematical formula, or pseudo-code ONLY if explicitly present in the source text. Otherwise null"\n'
            '    }\n'
            '  ],\n'
            '  "actionable_takeaways": ["High-level engineering takeaways, critical rules, or implementation checkpoints"]\n'
            "}\n\n"
            f"--- CONTEXT START ---\n{context_text.strip()[:14000]}\n--- CONTEXT END ---\n\n"
            "Remember: Zero mentions of authors, publishers, or licensing. Output only core engineering/academic substance."
        )
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are an expert engineering professor. Respond ONLY with a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_json = resp.choices[0].message.content
        data = json.loads(raw_json)
        return AdaptiveStudyNotes.model_validate(data)
    except Exception as exc:
        logger.warning(f"[GroqFailover] Groq adaptive study notes fallback failed: {exc}")
        return None


def _generate_with_mistral_adaptive_study_notes(
    topic: str,
    context_text: str,
    difficulty: DifficultyLevel = "intermediate",
) -> Optional[AdaptiveStudyNotes]:
    """Failover generator for AdaptiveStudyNotes using Mistral structured output."""
    api_key = getattr(settings, "MISTRAL_API_KEY", None)
    if not api_key:
        return None
    try:
        from langchain_mistralai import ChatMistralAI

        llm = ChatMistralAI(model="mistral-small-latest", api_key=api_key, temperature=0.2)
        structured_llm = llm.with_structured_output(AdaptiveStudyNotes)
        diff_instruction = get_difficulty_notes_prompt(difficulty)
        system_prompt = f"{ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT}\n\n{diff_instruction}"
        human_prompt = ADAPTIVE_STUDY_NOTES_USER_PROMPT.format(topic=topic, context_text=context_text.strip()[:14000])

        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        if isinstance(result, AdaptiveStudyNotes):
            return result
        elif isinstance(result, dict):
            return AdaptiveStudyNotes.model_validate(result)
    except Exception as exc:
        logger.warning(f"[MistralFailover] Mistral adaptive study notes fallback failed: {exc}")
        return None


def _generate_with_groq_study_notes(
    context_text: str,
    difficulty: DifficultyLevel = "intermediate",
) -> Optional[StudyNotes]:
    """Failover generator using Groq's high-speed JSON inference."""
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return None
    try:
        import json
        from groq import Groq

        client = Groq(api_key=api_key)
        diff_instruction = get_difficulty_notes_prompt(difficulty)
        prompt = (
            f"{STUDY_NOTES_SYSTEM_PROMPT}\n\n"
            f"{diff_instruction}\n\n"
            f"Respond ONLY with a valid JSON object matching this schema calibrated to '{difficulty}' difficulty:\n"
            "{\n"
            '  "topic_title": "Specific technical topic or domain covered",\n'
            '  "executive_summary": "2-3 dense academic paragraphs explaining core principles, engineering mechanics, and applications",\n'
            '  "core_concepts": [\n'
            '    {\n'
            '      "term": "Technical concept, keyword, or construct name",\n'
            '      "definition": "In-depth explanation of operational mechanics and behavior",\n'
            '      "syntax_or_example": "Markdown code snippet, syntax pattern, or formula illustrating usage or null"\n'
            '    }\n'
            '  ],\n'
            '  "syntax_and_formulas": ["Essential syntax rules, mathematical formulas in LaTeX, or code idioms"],\n'
            '  "high_yield_revision_points": ["High-yield exam takeaways: edge cases, common pitfalls, performance trade-offs, and critical rules"]\n'
            "}\n\n"
            f"--- CONTEXT START ---\n{context_text.strip()[:14000]}\n--- CONTEXT END ---\n\n"
            "Remember: Zero mentions of authors, publishers, or licensing. Output only core engineering/programming substance."
        )
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are an expert engineering professor. Respond ONLY with a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_json = resp.choices[0].message.content
        data = json.loads(raw_json)
        return StudyNotes.model_validate(data)
    except Exception as exc:
        logger.warning(f"[GroqFailover] Groq study notes fallback failed: {exc}")
        return None


def _generate_with_groq_quiz(
    context_text: str,
    num_questions: int = 20,
    difficulty: DifficultyLevel = "intermediate",
) -> Optional[QuizDeck]:
    """Failover generator for MCQs using Groq's high-speed JSON inference."""
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return None
    try:
        import json
        from groq import Groq

        client = Groq(api_key=api_key)
        diff_instruction = get_difficulty_mcq_prompt(difficulty)
        prompt = (
            f"You are an expert university examiner. Generate exactly {num_questions} rigorous multiple-choice questions "
            f"strictly grounded in the provided academic material calibrated to '{difficulty}' difficulty.\n\n"
            f"{diff_instruction}\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "title": "Academic Subject Quiz",\n'
            '  "questions": [\n'
            "    {\n"
            '      "question": "Question text",\n'
            '      "options": ["Choice A", "Choice B", "Choice C", "Choice D"],\n'
            '      "correct_index": 0,\n'
            '      "explanation": "Why this specific choice is correct",\n'
            '      "reference_page": null\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"--- CONTEXT START ---\n{context_text.strip()[:14000]}\n--- CONTEXT END ---"
        )
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a university examiner. Respond ONLY with a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_json = resp.choices[0].message.content
        data = json.loads(raw_json)
        return QuizDeck.model_validate(data)
    except Exception as exc:
        logger.warning(f"[GroqFailover] Groq MCQ quiz fallback failed: {exc}")
        return None


# ==============================================================================
# Generation Functions
# ==============================================================================

def generate_study_notes(
    context_text: str,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
    difficulty: DifficultyLevel = "intermediate",
) -> StudyNotes:
    """
    Generate structured, high-yield study notes from syllabus or lecture context.

    Uses Google Gemini with structured output enforcing the `StudyNotes` schema.
    Automatically cascades through candidate models and Groq if rate limits occur.
    """
    if not context_text or not context_text.strip():
        raise ValueError("context_text cannot be empty or whitespace only.")

    models_to_try = [model_name] + [m for m in CANDIDATE_STUDY_MODELS if m != model_name]
    last_error = None

    diff_instruction = get_difficulty_notes_prompt(difficulty)
    system_prompt = f"{STUDY_NOTES_SYSTEM_PROMPT}\n\n{diff_instruction}"
    human_prompt = STUDY_NOTES_USER_PROMPT.format(context_text=context_text.strip())

    for model in models_to_try:
        try:
            llm = _get_llm(model_name=model)
            structured_llm = llm.with_structured_output(StudyNotes)

            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            if isinstance(result, StudyNotes):
                return result
            elif isinstance(result, dict):
                return StudyNotes(**result)
            else:
                return StudyNotes.model_validate(result)
        except Exception as exc:
            logger.warning(f"[generate_study_notes] Model '{model}' failed: {exc}. Trying fallback...")
            last_error = exc

    # Attempt ultra-fast secondary provider failover (Groq)
    logger.info("[generate_study_notes] Gemini candidates exhausted; invoking Groq failover engine...")
    groq_result = _generate_with_groq_study_notes(context_text, difficulty=difficulty)
    if groq_result:
        return groq_result

    logger.error(f"[generate_study_notes] All candidate models failed. Last error: {last_error}")
    raise RuntimeError(f"Failed to generate structured study notes: {last_error}") from last_error


async def generate_study_notes_async(
    context_text: str,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
    difficulty: DifficultyLevel = "intermediate",
) -> StudyNotes:
    """Asynchronous non-blocking wrapper around generate_study_notes."""
    return await asyncio.to_thread(generate_study_notes, context_text, model_name, difficulty)


def generate_adaptive_study_notes(
    topic: str,
    context_text: Optional[str] = None,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
    context: Optional[str] = None,
    difficulty: DifficultyLevel = "intermediate",
) -> AdaptiveStudyNotes:
    """
    Generate document-adaptive study notes eliminating rigid syntax/formula and fake exam assumptions.

    Cascades through Google Gemini -> Mistral AI -> Groq failover.
    Accepts context either as `context_text` or `context`.
    """
    if not topic or not topic.strip():
        topic = "Core Academic Subject"

    raw_context = context if context is not None else (context_text or "")
    if not raw_context or not raw_context.strip():
        raw_context = f"Topic: {topic.strip()}. Core engineering curriculum principles, architectural tracks, and concrete deliverables."

    models_to_try = [model_name] + [m for m in CANDIDATE_STUDY_MODELS if m != model_name]
    last_error = None

    diff_instruction = get_difficulty_notes_prompt(difficulty)
    system_prompt = f"{ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT}\n\n{diff_instruction}"
    human_prompt = ADAPTIVE_STUDY_NOTES_USER_PROMPT.format(
        topic=topic.strip(),
        context_text=raw_context.strip()[:14000],
    )

    # 1. Primary: Google Gemini candidates
    for model in models_to_try:
        try:
            llm = _get_llm(model_name=model)
            structured_llm = llm.with_structured_output(AdaptiveStudyNotes)

            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            if isinstance(result, AdaptiveStudyNotes):
                return result
            elif isinstance(result, dict):
                return AdaptiveStudyNotes.model_validate(result)
            else:
                return AdaptiveStudyNotes.model_validate(result)
        except Exception as exc:
            logger.warning(f"[generate_adaptive_study_notes] Gemini model '{model}' failed: {exc}. Trying next candidate...")
            last_error = exc

    # 2. Secondary: Mistral AI failover
    logger.info("[generate_adaptive_study_notes] Gemini candidates exhausted; trying Mistral failover...")
    mistral_result = _generate_with_mistral_adaptive_study_notes(topic, raw_context, difficulty=difficulty)
    if mistral_result:
        return mistral_result

    # 3. Tertiary: Groq failover
    logger.info("[generate_adaptive_study_notes] Mistral exhausted; trying Groq failover...")
    groq_result = _generate_with_groq_adaptive_study_notes(topic, raw_context, difficulty=difficulty)
    if groq_result:
        return groq_result

    logger.error(f"[generate_adaptive_study_notes] All candidate models failed. Last error: {last_error}")
    raise RuntimeError(f"Failed to generate adaptive study notes: {last_error}") from last_error


async def generate_adaptive_study_notes_async(
    topic: str,
    context_text: Optional[str] = None,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
    context: Optional[str] = None,
    difficulty: DifficultyLevel = "intermediate",
) -> AdaptiveStudyNotes:
    """Asynchronous non-blocking wrapper around generate_adaptive_study_notes."""
    return await asyncio.to_thread(generate_adaptive_study_notes, topic, context_text, model_name, context, difficulty)


def generate_topic_study_notes(
    topic: str,
    context_text: str,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
    difficulty: DifficultyLevel = "intermediate",
) -> AdaptiveStudyNotes:
    """
    Generate structured study notes for a specific academic topic.
    Delegates to the dynamic AdaptiveStudyNotes engine.
    """
    return generate_adaptive_study_notes(topic, context_text, model_name, difficulty=difficulty)


async def generate_topic_study_notes_async(
    topic: str,
    context_text: str,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
    difficulty: DifficultyLevel = "intermediate",
) -> AdaptiveStudyNotes:
    """Asynchronous non-blocking wrapper around generate_topic_study_notes."""
    return await generate_adaptive_study_notes_async(topic, context_text, model_name, difficulty=difficulty)


def generate_mcq_quiz(
    context_text: str,
    num_questions: int = 20,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
    difficulty: DifficultyLevel = "intermediate",
) -> QuizDeck:
    """
    Generate an academic multiple-choice quiz from syllabus or course context.
    Calibrated strictly by difficulty ('beginner', 'intermediate', 'advanced').

    Uses Google Gemini with structured output enforcing the `QuizDeck` schema.
    Automatically cascades through candidate models and Groq if rate limits occur.
    """
    if not context_text or not context_text.strip():
        raise ValueError("context_text cannot be empty or whitespace only.")

    if num_questions < 1:
        raise ValueError("num_questions must be at least 1.")

    models_to_try = [model_name] + [m for m in CANDIDATE_STUDY_MODELS if m != model_name]
    last_error = None

    diff_instruction = get_difficulty_mcq_prompt(difficulty)
    system_prompt = (
        "You are an expert university examiner. Your task is to generate rigorous, "
        "academically calibrated multiple-choice questions (MCQs) strictly grounded in the provided syllabus context.\n"
        f"{diff_instruction}\n"
        f"Generate exactly {num_questions} questions.\n"
        "Requirements:\n"
        "- Each question must have exactly 4 distinct answer choices in 'options'.\n"
        "- 'correct_index' must be an integer between 0 and 3 indicating the zero-based index of the right option.\n"
        "- 'explanation' must clearly justify why that specific option is correct based on the calibrated difficulty.\n"
        "- If a specific syllabus page number is explicitly referenced in the context, set 'reference_page' accordingly; otherwise null."
    )

    human_prompt = (
        f"Generate a quiz deck with exactly {num_questions} questions at '{difficulty}' difficulty level based on the following material:\n\n"
        f"--- CONTEXT START ---\n{context_text.strip()}\n--- CONTEXT END ---"
    )

    for model in models_to_try:
        try:
            llm = _get_llm(model_name=model)
            structured_llm = llm.with_structured_output(QuizDeck)

            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            if isinstance(result, QuizDeck):
                return result
            elif isinstance(result, dict):
                return QuizDeck(**result)
            else:
                return QuizDeck.model_validate(result)
        except Exception as exc:
            logger.warning(f"[generate_mcq_quiz] Model '{model}' failed: {exc}. Trying fallback...")
            last_error = exc

    # Attempt ultra-fast secondary provider failover (Groq)
    logger.info("[generate_mcq_quiz] Gemini candidates exhausted; invoking Groq failover engine...")
    groq_result = _generate_with_groq_quiz(context_text, num_questions=num_questions, difficulty=difficulty)
    if groq_result:
        return groq_result

    logger.error(f"[generate_mcq_quiz] All candidate models failed. Last error: {last_error}")
    raise RuntimeError(f"Failed to generate structured MCQ quiz: {last_error}") from last_error


async def generate_mcq_quiz_async(
    context_text: str,
    num_questions: int = 20,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
    difficulty: DifficultyLevel = "intermediate",
) -> QuizDeck:
    """Asynchronous non-blocking wrapper around generate_mcq_quiz."""
    return await asyncio.to_thread(generate_mcq_quiz, context_text, num_questions, model_name, difficulty)


COMPLETE_PACK_SYSTEM_PROMPT = """You are a premier university professor and curriculum director.
Your objective is to generate an exhaustive, publication-quality Complete Study Pack based strictly on the provided course material.

CALIBRATION BY DIFFICULTY:
- "beginner": Focus on definitions, core concepts, foundational principles, and straightforward options in MCQs.
- "intermediate": Focus on operational mechanics, practical implementation, standard engineering trade-offs, and analytical relationships.
- "advanced": Focus on multi-step architectural derivations, subtle edge cases, failure modes, performance trade-offs, and rigorous grading criteria.

EXACT QUANTITY REQUIREMENTS:
1. Title: Subject title or main lecture topic.
2. Difficulty: Must reflect the target difficulty ("beginner", "intermediate", or "advanced").
3. Concise Summary: Dense, structured academic notes covering all core themes from the material.
4. Suggested Study Order: Step-by-step recommended study progression (4-8 logical steps).
5. Glossary: Key terms glossary containing 8-15 core technical terms with concise, precise academic definitions.
6. MCQs: EXACTLY 20 practice multiple choice questions. Each question must have exactly 4 choices (options), the verbatim text of the correct choice (correct_answer), and a detailed conceptual explanation.
7. Short Answers: EXACTLY 5 conceptual or analytical questions. Each must feature a comprehensive model_answer and 3-5 specific grading_criteria bullet points.
"""

COMPLETE_PACK_USER_PROMPT = """Generate a Complete Study Pack calibrated to the "{difficulty}" difficulty level from the following context:

--- CONTEXT START ---
{context}
--- CONTEXT END ---

Generate the complete study pack with concise summary notes, suggested study order roadmap, glossary, EXACTLY 20 practice MCQs, and EXACTLY 5 short-answer questions with grading criteria."""


def generate_complete_study_pack(
    context: str,
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate",
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
) -> CompleteStudyPack:
    """
    Generate an all-inclusive CompleteStudyPack:
    - Concise summary notes
    - 20 practice MCQs with explanations
    - 5 short-answer questions with model answers and evaluation rubrics
    - Key terms glossary
    - Suggested study progression
    - Difficulty calibration ("beginner", "intermediate", "advanced")
    """
    if not context or not context.strip():
        raise ValueError("Context cannot be empty for study pack generation.")

    models_to_try = [model_name] + [m for m in CANDIDATE_STUDY_MODELS if m != model_name]
    last_error = None

    for model in models_to_try:
        try:
            llm = _get_llm(model_name=model)
            structured_llm = llm.with_structured_output(CompleteStudyPack)

            system_prompt = COMPLETE_PACK_SYSTEM_PROMPT
            human_prompt = COMPLETE_PACK_USER_PROMPT.format(
                difficulty=difficulty,
                context=context.strip()[:35000],
            )

            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            if isinstance(result, CompleteStudyPack):
                return result
            elif isinstance(result, dict):
                return CompleteStudyPack.model_validate(result)
            else:
                return CompleteStudyPack.model_validate(result)
        except Exception as exc:
            logger.warning(f"[generate_complete_study_pack] Model '{model}' failed: {exc}. Trying fallback...")
            last_error = exc

    logger.error(f"[generate_complete_study_pack] All candidate models failed. Last error: {last_error}")
    raise RuntimeError(f"Failed to generate Complete Study Pack: {last_error}") from last_error


async def generate_complete_study_pack_async(
    context: str,
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate",
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
) -> CompleteStudyPack:
    """Asynchronous non-blocking wrapper around generate_complete_study_pack."""
    return await asyncio.to_thread(generate_complete_study_pack, context, difficulty, model_name)


__all__ = [
    "MCQItem",
    "ShortAnswerItem",
    "GlossaryItem",
    "CompleteStudyPack",
    "QuizDeck",
    "ConceptBlock",
    "TopicStudyNotes",
    "ConceptDefinition",
    "StudyNotes",
    "TopicDetailBlock",
    "AdaptiveStudyNotes",
    "generate_study_notes",
    "generate_study_notes_async",
    "generate_topic_study_notes",
    "generate_topic_study_notes_async",
    "generate_adaptive_study_notes",
    "generate_adaptive_study_notes_async",
    "generate_mcq_quiz",
    "generate_mcq_quiz_async",
    "generate_complete_study_pack",
    "generate_complete_study_pack_async",
]

