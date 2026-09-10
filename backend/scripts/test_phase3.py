"""
scripts/test_phase3.py
----------------------
Standalone verification script for Phase 3:
1. Verifies Pydantic schemas (MCQItem, QuizDeck, StudyNotes).
2. Verifies generate_mcq_quiz with dummy syllabus text.
3. Verifies generate_study_notes with dummy syllabus text.
4. Verifies validation on empty input.
5. Verifies tool registration and signatures in app.tools.
"""

import sys
import os

# Ensure UTF-8 output on Windows consoles
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tools import (
    LOCAL_TOOLS,
    TOOL_METADATA,
    syllabus_rag_search,
    syllabus_rag_search_async,
    web_search_tool,
)
from app.services.study_generator import (
    MCQItem,
    QuizDeck,
    StudyNotes,
    generate_mcq_quiz,
    generate_study_notes,
)

SAMPLE_CONTEXT = """
Course Code: 22ECE301
Course Title: Signals and Systems
Semester: 3
Unit I: Classification of Signals and Systems
Continuous-time (CT) and Discrete-time (DT) signals: Periodic vs. Aperiodic, Energy and Power signals,
Even and Odd signals. Transformation of independent variable: time shifting, time reversal, time scaling.
Basic continuous and discrete time signals: unit impulse, unit step, ramp, sinusoidal, exponential signals.
Classification of systems: Linear and Non-linear, Time-Invariant and Time-Variant, Causal and Non-Causal,
Stable and Unstable (BIBO stability criterion).
Convolution integral for CT LTI systems: y(t) = x(t) * h(t) = \\int_{-\\infty}^{\\infty} x(\\tau) h(t-\\tau) d\\tau.
"""

def main():
    print("=" * 60)
    print("PHASE 3 VERIFICATION TEST SUITE")
    print("=" * 60)

    # 1. Tool registry verification
    print("\n[1] Checking Tool Registry...")
    tool_names = [t.name for t in LOCAL_TOOLS]
    print(f"Active tools: {tool_names}")
    assert "syllabus_rag_search" in tool_names, "Missing syllabus_rag_search"
    assert "web_search_tool" in tool_names, "Missing web_search_tool"
    assert "calculate_cgpa" not in tool_names, "CGPA tool should be excluded!"
    print(f"Tool metadata: {TOOL_METADATA}")
    print("[PASS] Tool registry verification passed.")

    # 2. Empty text validation
    print("\n[2] Checking input validation...")
    try:
        generate_mcq_quiz("   ")
        print("[FAIL] Empty text should have raised ValueError!")
        sys.exit(1)
    except ValueError as e:
        print(f"[PASS] Empty text correctly caught: {e}")

    # 3. Test generate_mcq_quiz
    print("\n[3] Testing generate_mcq_quiz with dummy syllabus text...")
    quiz = generate_mcq_quiz(SAMPLE_CONTEXT, num_questions=2)
    print(f"Quiz Title: {quiz.title}")
    print(f"Total Questions Generated: {len(quiz.questions)}")
    assert isinstance(quiz, QuizDeck), "Result is not an instance of QuizDeck"
    assert len(quiz.questions) >= 1, "No questions generated"

    for i, q in enumerate(quiz.questions, start=1):
        assert isinstance(q, MCQItem), f"Question {i} is not an MCQItem"
        print(f"\n  Q{i}: {q.question}")
        assert len(q.options) == 4, f"Question {i} must have 4 options, got {len(q.options)}"
        for idx, opt in enumerate(q.options):
            marker = "*" if idx == q.correct_index else " "
            print(f"    [{idx}]{marker} {opt}")
        print(f"    Explanation: {q.explanation}")
        assert 0 <= q.correct_index <= 3, f"Invalid correct_index {q.correct_index}"
    print("\n[PASS] generate_mcq_quiz successfully generated and validated QuizDeck!")

    # 4. Test generate_study_notes
    print("\n[4] Testing generate_study_notes with dummy syllabus text...")
    notes = generate_study_notes(SAMPLE_CONTEXT)
    assert isinstance(notes, StudyNotes), "Result is not an instance of StudyNotes"
    print(f"Summary: {notes.executive_summary[:120]}...")
    print(f"Key Concepts: {len(notes.key_concepts)} extracted")
    print(f"Formulas: {notes.formulas_and_theorems}")
    print(f"Revision Points: {len(notes.high_yield_revision_points)} points")
    print("[PASS] generate_study_notes successfully generated and validated StudyNotes!")

    print("\n" + "=" * 60)
    print("ALL PHASE 3 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
