"""
scripts/test_difficulty_calibration.py
--------------------------------------
Automated verification for difficulty-calibrated study notes and MCQ generation pipelines.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.study_generator import (
    DifficultyLevel,
    get_difficulty_notes_prompt,
    get_difficulty_mcq_prompt,
    generate_adaptive_study_notes,
    generate_mcq_quiz,
    QuizDeck,
    MCQItem,
)
from app.routes.study import (
    StudyNotesRequest,
    TopicNotesRequest,
    MCQRequest,
    ExportNotesRequest,
)


class TestDifficultyCalibration(unittest.TestCase):

    def test_difficulty_notes_prompts(self):
        """Verify distinct calibration guidance per difficulty tier for study notes."""
        beginner = get_difficulty_notes_prompt("beginner")
        intermediate = get_difficulty_notes_prompt("intermediate")
        advanced = get_difficulty_notes_prompt("advanced")

        self.assertIn("CALIBRATION LEVEL - BEGINNER", beginner)
        self.assertIn("Foundational and conceptual", beginner)

        self.assertIn("CALIBRATION LEVEL - INTERMEDIATE", intermediate)
        self.assertIn("operational mechanics", intermediate)

        self.assertIn("CALIBRATION LEVEL - ADVANCED", advanced)
        self.assertIn("theoretical rigor", advanced)

        # Confirm all tiers are distinct
        self.assertNotEqual(beginner, intermediate)
        self.assertNotEqual(intermediate, advanced)
        self.assertNotEqual(beginner, advanced)

    def test_difficulty_mcq_prompts(self):
        """Verify distinct calibration guidance per difficulty tier for MCQs."""
        beginner = get_difficulty_mcq_prompt("beginner")
        intermediate = get_difficulty_mcq_prompt("intermediate")
        advanced = get_difficulty_mcq_prompt("advanced")

        self.assertIn("CALIBRATION LEVEL - BEGINNER", beginner)
        self.assertIn("Foundational recall", beginner)

        self.assertIn("CALIBRATION LEVEL - INTERMEDIATE", intermediate)
        self.assertIn("Application-oriented reasoning", intermediate)

        self.assertIn("CALIBRATION LEVEL - ADVANCED", advanced)
        self.assertIn("Multi-step reasoning", advanced)

        # Confirm all tiers are distinct
        self.assertNotEqual(beginner, intermediate)
        self.assertNotEqual(intermediate, advanced)
        self.assertNotEqual(beginner, advanced)

    def test_request_models_difficulty_support(self):
        """Verify that FastAPI request schemas validate difficulty and default to 20 MCQs."""
        # 1. StudyNotesRequest
        sn_default = StudyNotesRequest(doc_id="doc123")
        self.assertEqual(sn_default.difficulty, "intermediate")

        sn_adv = StudyNotesRequest(doc_id="doc123", difficulty="advanced")
        self.assertEqual(sn_adv.difficulty, "advanced")

        # 2. TopicNotesRequest
        tn_beg = TopicNotesRequest(topic="Pointers", difficulty="beginner")
        self.assertEqual(tn_beg.difficulty, "beginner")

        # 3. MCQRequest - default count must be 20
        mcq_default = MCQRequest(doc_id="doc123")
        self.assertEqual(mcq_default.count, 20)
        self.assertEqual(mcq_default.difficulty, "intermediate")

        mcq_adv = MCQRequest(doc_id="doc123", count=20, difficulty="advanced")
        self.assertEqual(mcq_adv.count, 20)
        self.assertEqual(mcq_adv.difficulty, "advanced")

        # 4. ExportNotesRequest
        exp_req = ExportNotesRequest(topic="Testing", difficulty="advanced")
        self.assertEqual(exp_req.difficulty, "advanced")

    def test_mcq_item_validation(self):
        """Verify MCQItem schema validation and correct_index syncing."""
        item = MCQItem(
            question="What is the time complexity of binary search?",
            options=["O(1)", "O(log n)", "O(n)", "O(n^2)"],
            correct_index=1,
            explanation="Binary search halves the search space each step.",
        )
        self.assertEqual(item.correct_answer, "O(log n)")
        self.assertEqual(item.correct_index, 1)


if __name__ == "__main__":
    unittest.main()
