"""
app/services
------------
Business logic and generation services for study notes and quizzes.
"""

from .study_generator import (
    AdaptiveStudyNotes,
    ConceptBlock,
    ConceptDefinition,
    MCQItem,
    QuizDeck,
    StudyNotes,
    TopicDetailBlock,
    TopicStudyNotes,
    generate_adaptive_study_notes,
    generate_adaptive_study_notes_async,
    generate_mcq_quiz,
    generate_mcq_quiz_async,
    generate_study_notes,
    generate_study_notes_async,
    generate_topic_study_notes,
    generate_topic_study_notes_async,
)

__all__ = [
    "AdaptiveStudyNotes",
    "ConceptBlock",
    "ConceptDefinition",
    "MCQItem",
    "QuizDeck",
    "StudyNotes",
    "TopicDetailBlock",
    "TopicStudyNotes",
    "generate_adaptive_study_notes",
    "generate_adaptive_study_notes_async",
    "generate_study_notes",
    "generate_study_notes_async",
    "generate_topic_study_notes",
    "generate_topic_study_notes_async",
    "generate_mcq_quiz",
    "generate_mcq_quiz_async",
]
