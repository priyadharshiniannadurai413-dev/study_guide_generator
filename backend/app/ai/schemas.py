"""
app/ai/schemas.py
------------------
Shared Pydantic schemas used across all LangGraph agents.
Extracted from the former study_generator.py for reuse by
Curriculum, StudyNotes, MCQ, and Supervisor agents.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ── MCQ Schemas ───────────────────────────────────────────────────────────────

class MCQItem(BaseModel):
    """A single multiple-choice question with 4 options and answer explanation."""

    question: str = Field(description="The question prompt")
    options: List[str] = Field(description="Exactly 4 distinct answer choices")
    correct_index: int = Field(description="Index (0-3) of the correct answer")
    explanation: str = Field(description="Detailed explanation why this option is correct")
    reference_page: Optional[int] = Field(default=None, description="Source page number")


class QuizDeck(BaseModel):
    """Collection of multiple-choice questions forming an academic quiz."""

    title: str = Field(description="Quiz topic or title")
    questions: List[MCQItem] = Field(description="List of generated MCQs")


# ── Study Notes Schemas ───────────────────────────────────────────────────────

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

    def to_adaptive_study_notes(self) -> "AdaptiveStudyNotes":
        """Convert StudyNotes to AdaptiveStudyNotes."""
        return AdaptiveStudyNotes(
            title=self.topic_title,
            executive_summary=self.executive_summary,
            sections=[
                TopicDetailBlock(
                    title=c.term,
                    overview=c.definition,
                    key_points=[],
                    code_or_syntax=c.syntax_or_example,
                )
                for c in self.core_concepts
            ],
            actionable_takeaways=list(self.high_yield_revision_points),
        )


# ── Adaptive Curriculum & Topic Study Notes Schemas ──────────────────────────

class TopicDetailBlock(BaseModel):
    """A granular section, module, or project block in adaptive study notes."""

    title: str = Field(description="Subtopic, module name, or project title")
    overview: str = Field(description="Clear explanation of the concept, purpose, or architecture")
    key_points: List[str] = Field(
        default_factory=list,
        description="Concrete details, requirements, core principles, or components"
    )
    code_or_syntax: Optional[str] = Field(
        default=None,
        description="Verbatim code snippet, mathematical formula, or pseudo-code ONLY if explicitly present in the source text. Otherwise None."
    )


class AdaptiveStudyNotes(BaseModel):
    """Document-adaptive study notes eliminating rigid syntax/formula and fake exam assumptions."""

    title: str = Field(description="Document subject or primary topic title")
    executive_summary: str = Field(description="2-3 dense paragraphs providing a holistic synthesis of the material")
    sections: List[TopicDetailBlock] = Field(
        default_factory=list,
        description="Structured breakdown of core sections, modules, or architectural components"
    )
    actionable_takeaways: List[str] = Field(
        default_factory=list,
        description="High-level engineering takeaways, critical rules, or implementation checkpoints"
    )

    # Backward-compatible fields
    topic_title: Optional[str] = None
    quick_summary: Optional[str] = None
    key_takeaways: Optional[List[str]] = None
    concepts: Optional[List[Dict[str, Any]]] = None
    common_pitfalls: Optional[List[str]] = None
    core_concepts: Optional[List[Dict[str, Any]]] = None
    syntax_and_formulas: Optional[List[str]] = None
    high_yield_revision_points: Optional[List[str]] = None
    external_references: Optional[List[Dict[str, str]]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "title" not in data and "topic_title" in data:
                data["title"] = data["topic_title"]
            if "executive_summary" not in data and "quick_summary" in data:
                data["executive_summary"] = data["quick_summary"]
            if "sections" not in data:
                if "concepts" in data:
                    raw = data.get("concepts") or []
                    converted = []
                    for c in raw:
                        if isinstance(c, dict):
                            kp = [c["practical_example"]] if c.get("practical_example") else []
                            converted.append({
                                "title": c.get("subtopic") or c.get("title") or "Section",
                                "overview": c.get("explanation") or c.get("overview") or "",
                                "key_points": kp,
                                "code_or_syntax": c.get("syntax_or_formula"),
                            })
                    data["sections"] = converted
                elif "core_concepts" in data:
                    raw = data.get("core_concepts") or []
                    converted = []
                    for c in raw:
                        if isinstance(c, dict):
                            converted.append({
                                "title": c.get("term") or c.get("concept") or "Concept",
                                "overview": c.get("definition") or "",
                                "key_points": [],
                                "code_or_syntax": c.get("syntax_or_example"),
                            })
                    data["sections"] = converted
            if "actionable_takeaways" not in data:
                if "key_takeaways" in data:
                    data["actionable_takeaways"] = data.get("key_takeaways") or []
                elif "high_yield_revision_points" in data:
                    data["actionable_takeaways"] = data.get("high_yield_revision_points") or []
        return data

    @model_validator(mode="after")
    def populate_compatibility_fields(self) -> "AdaptiveStudyNotes":
        if not self.topic_title:
            self.topic_title = self.title
        if not self.quick_summary:
            self.quick_summary = self.executive_summary
        if self.key_takeaways is None:
            self.key_takeaways = list(self.actionable_takeaways)
        if self.high_yield_revision_points is None:
            self.high_yield_revision_points = list(self.actionable_takeaways)
        if self.common_pitfalls is None:
            self.common_pitfalls = []
        if self.concepts is None:
            self.concepts = [
                {
                    "subtopic": s.title,
                    "explanation": s.overview,
                    "syntax_or_formula": s.code_or_syntax,
                    "practical_example": "\n".join(f"• {p}" for p in s.key_points) if s.key_points else None,
                }
                for s in self.sections
            ]
        if self.core_concepts is None:
            self.core_concepts = [
                {
                    "term": s.title,
                    "definition": s.overview + (("\nKey points:\n" + "\n".join(f"- {p}" for p in s.key_points)) if s.key_points else ""),
                    "syntax_or_example": s.code_or_syntax,
                }
                for s in self.sections
            ]
        if self.syntax_and_formulas is None:
            self.syntax_and_formulas = [s.code_or_syntax for s in self.sections if s.code_or_syntax]
        return self


# ── Router Schemas ────────────────────────────────────────────────────────────

class RouteDecision(BaseModel):
    """Structured output from the supervisor router node."""

    route: Literal["curriculum", "study_notes", "mcq", "direct_answer", "github"] = Field(
        description=(
            "The classified intent route. Must be exactly one of: "
            "curriculum, study_notes, mcq, direct_answer, github"
        )
    )


__all__ = [
    "MCQItem",
    "QuizDeck",
    "ConceptDefinition",
    "StudyNotes",
    "TopicDetailBlock",
    "AdaptiveStudyNotes",
    "RouteDecision",
]
