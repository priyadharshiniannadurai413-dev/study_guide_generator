import React, { useState } from 'react';
import {
  Award,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCheck2,
  FileText,
  HelpCircle,
  Info,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  XCircle,
} from 'lucide-react';
import { endpoints } from '../../api/endpoints';
import { DocumentSelector } from '../DocumentSelector';
import { useToast } from '../../context/ToastContext';

export interface TwoMarkQuestion {
  question_id: string;
  question: string;
  model_answer: string;
  key_points: string[];
}

export interface TwoMarkTestDeck {
  topic: string;
  total_marks: number;
  questions: TwoMarkQuestion[];
}

export interface EvaluationResult {
  question_id: string;
  score_awarded: number;
  max_marks: number;
  points_covered: string[];
  points_missed: string[];
  feedback: string;
  model_answer: string;
}

interface Props {
  initialDocId?: string;
}

export const TwoMarkTestArena: React.FC<Props> = ({ initialDocId = 'syllabus' }) => {
  const { addToast } = useToast();

  // Source selection state
  const [sourceType, setSourceType] = useState<'document' | 'pasted'>('document');
  const [selectedDocId, setSelectedDocId] = useState<string>(initialDocId);
  const [pastedText, setPastedText] = useState<string>('');
  const [questionCount, setQuestionCount] = useState<number>(5);

  // Test data & answering state
  const [testDeck, setTestDeck] = useState<TwoMarkTestDeck | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [studentAnswers, setStudentAnswers] = useState<Record<string, string>>({});
  const [evaluations, setEvaluations] = useState<Record<string, EvaluationResult>>({});
  const [evaluatingMap, setEvaluatingMap] = useState<Record<string, boolean>>({});
  const [expandedModelAnswers, setExpandedModelAnswers] = useState<Record<string, boolean>>({});
  const [isEvaluatingAll, setIsEvaluatingAll] = useState<boolean>(false);

  // Handle generating a new test
  const handleGenerateTest = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    if (sourceType === 'document' && !selectedDocId) {
      addToast('Please select a document source.', 'warning');
      return;
    }
    if (sourceType === 'pasted' && !pastedText.trim()) {
      addToast('Please paste lecture notes or syllabus text.', 'warning');
      return;
    }

    try {
      setIsGenerating(true);
      setTestDeck(null);
      setStudentAnswers({});
      setEvaluations({});
      setExpandedModelAnswers({});

      const deck: TwoMarkTestDeck = await endpoints.generateTwoMarkTest({
        docId: sourceType === 'document' ? selectedDocId : undefined,
        pastedText: sourceType === 'pasted' ? pastedText.trim() : undefined,
        count: questionCount,
      });

      if (!deck?.questions || deck.questions.length === 0) {
        throw new Error('No test questions were generated. Please try again.');
      }

      setTestDeck(deck);
      addToast(`Generated Part-A test with ${deck.questions.length} questions!`, 'success');
    } catch (err: any) {
      console.error('[TwoMarkTestArena] Test generation error:', err);
      addToast(err?.message || 'Failed to generate 2-mark test.', 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  // Handle single question evaluation
  const handleEvaluateQuestion = async (q: TwoMarkQuestion) => {
    const answer = studentAnswers[q.question_id]?.trim();
    if (!answer) {
      addToast(`Please write an answer for ${q.question_id} before submitting.`, 'warning');
      return;
    }

    try {
      setEvaluatingMap((prev) => ({ ...prev, [q.question_id]: true }));
      const result: EvaluationResult = await endpoints.evaluateAnswer({
        questionId: q.question_id,
        question: q.question,
        modelAnswer: q.model_answer,
        keyPoints: q.key_points,
        studentAnswer: answer,
      });

      setEvaluations((prev) => ({ ...prev, [q.question_id]: result }));
      const scoreWord = result.score_awarded === 2 ? 'Full marks (2/2)!' : result.score_awarded === 1 ? '1/2 marks awarded.' : '0/2 marks.';
      addToast(`${q.question_id} evaluated: ${scoreWord}`, result.score_awarded > 0 ? 'success' : 'warning');
    } catch (err: any) {
      console.error(`[TwoMarkTestArena] Evaluation failed for ${q.question_id}:`, err);
      addToast(`Failed to evaluate ${q.question_id}: ${err?.message}`, 'error');
    } finally {
      setEvaluatingMap((prev) => ({ ...prev, [q.question_id]: false }));
    }
  };

  // Handle batch evaluation for all answered questions
  const handleEvaluateAll = async () => {
    if (!testDeck) return;
    const answeredQuestions = testDeck.questions.filter(
      (q) => studentAnswers[q.question_id]?.trim() && !evaluations[q.question_id]
    );

    if (answeredQuestions.length === 0) {
      addToast('No new answered questions ready for evaluation.', 'warning');
      return;
    }

    try {
      setIsEvaluatingAll(true);
      for (const q of answeredQuestions) {
        setEvaluatingMap((prev) => ({ ...prev, [q.question_id]: true }));
        try {
          const result: EvaluationResult = await endpoints.evaluateAnswer({
            questionId: q.question_id,
            question: q.question,
            modelAnswer: q.model_answer,
            keyPoints: q.key_points,
            studentAnswer: studentAnswers[q.question_id].trim(),
          });
          setEvaluations((prev) => ({ ...prev, [q.question_id]: result }));
        } catch (subErr) {
          console.error(`Error grading ${q.question_id}:`, subErr);
        } finally {
          setEvaluatingMap((prev) => ({ ...prev, [q.question_id]: false }));
        }
      }
      addToast('Finished evaluating submitted answers!', 'success');
    } finally {
      setIsEvaluatingAll(false);
    }
  };

  // Toggle model answer accordion
  const toggleModelAnswer = (questionId: string) => {
    setExpandedModelAnswers((prev) => ({
      ...prev,
      [questionId]: !prev[questionId],
    }));
  };

  // Cumulative score statistics
  const totalQuestions = testDeck?.questions.length || 0;
  const maxPossibleMarks = totalQuestions * 2;
  const evaluatedCount = Object.keys(evaluations).length;
  const totalScoreAwarded = Object.values(evaluations).reduce(
    (acc, curr) => acc + (curr.score_awarded || 0),
    0
  );

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '32px 20px' }}>
      {/* Header Banner */}
      <div style={{ marginBottom: '32px', textAlign: 'center' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(99, 102, 241, 0.12)',
            border: '1px solid var(--border-accent)',
            color: '#a5b4fc',
            fontSize: '13px',
            fontWeight: 600,
            marginBottom: '12px',
          }}
        >
          <FileCheck2 size={16} />
          <span>Part-A Academic Testing Engine</span>
        </div>
        <h1
          style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '32px',
            fontWeight: 800,
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
            marginBottom: '8px',
          }}
        >
          2-Mark Conceptual Test Arena
        </h1>
        <p
          style={{
            color: 'var(--text-secondary)',
            fontSize: '15px',
            maxWidth: '680px',
            margin: '0 auto',
          }}
        >
          Synthesize high-yield, Part-A exam questions strictly from your lecture notes.
          Submit concise definitions and trade-offs to receive instant, semantic AI evaluation.
        </p>
      </div>

      {/* Generator Configuration Panel */}
      <div
        style={{
          background: 'var(--bg-card)',
          backdropFilter: 'blur(16px)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          marginBottom: '32px',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '20px',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '16px',
          }}
        >
          <button
            type="button"
            onClick={() => setSourceType('document')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: sourceType === 'document' ? 'var(--primary)' : 'transparent',
              color: sourceType === 'document' ? '#ffffff' : 'var(--text-secondary)',
              fontWeight: 600,
              fontSize: '14px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <FileText size={16} />
            <span>Uploaded Document</span>
          </button>
          <button
            type="button"
            onClick={() => setSourceType('pasted')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: sourceType === 'pasted' ? 'var(--primary)' : 'transparent',
              color: sourceType === 'pasted' ? '#ffffff' : 'var(--text-secondary)',
              fontWeight: 600,
              fontSize: '14px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <BookOpen size={16} />
            <span>Pasted Syllabus / Notes</span>
          </button>
        </div>

        <form onSubmit={handleGenerateTest}>
          {sourceType === 'document' ? (
            <div style={{ marginBottom: '20px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '8px',
                }}
              >
                Knowledge Source Document:
              </label>
              <DocumentSelector
                selectedDocId={selectedDocId}
                onSelectDocId={setSelectedDocId}
              />
            </div>
          ) : (
            <div style={{ marginBottom: '20px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '8px',
                }}
              >
                Paste Lecture Text or Syllabus Context:
              </label>
              <textarea
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                placeholder="Paste specific lecture slides, textbook sections, or syllabus concepts here..."
                rows={5}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  resize: 'vertical',
                  outline: 'none',
                }}
              />
            </div>
          )}

          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Questions:
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {[5, 10].map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => setQuestionCount(num)}
                    style={{
                      padding: '6px 14px',
                      borderRadius: 'var(--radius-sm)',
                      background: questionCount === num ? 'var(--bg-tertiary)' : 'transparent',
                      border: questionCount === num ? '1px solid var(--border-accent)' : '1px solid var(--border-subtle)',
                      color: questionCount === num ? 'var(--text-primary)' : 'var(--text-muted)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                    }}
                  >
                    {num} Qs ({num * 2} Marks)
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={isGenerating}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 22px',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
                color: '#ffffff',
                fontWeight: 600,
                fontSize: '14px',
                cursor: isGenerating ? 'not-allowed' : 'pointer',
                opacity: isGenerating ? 0.7 : 1,
                boxShadow: 'var(--shadow-glow)',
                transition: 'all 0.2s ease',
              }}
            >
              {isGenerating ? (
                <>
                  <Loader2 size={16} className="spin" />
                  <span>Synthesizing Exam...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Generate 2-Mark Test</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Test Arena Content */}
      {testDeck && (
        <div>
          {/* Progress & Sticky Action Toolbar */}
          <div
            style={{
              position: 'sticky',
              top: '78px',
              zIndex: 30,
              background: 'rgba(17, 24, 39, 0.92)',
              backdropFilter: 'blur(16px)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '16px 20px',
              marginBottom: '24px',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              boxShadow: 'var(--shadow-card)',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3
                  style={{
                    fontSize: '17px',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-heading)',
                  }}
                >
                  {testDeck.topic || 'Part-A Examination Deck'}
                </h3>
                <span
                  style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-full)',
                    background: 'rgba(99, 102, 241, 0.2)',
                    color: '#c7d2fe',
                    border: '1px solid var(--border-accent)',
                  }}
                >
                  {testDeck.total_marks || maxPossibleMarks} Marks Total
                </span>
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Evaluated: <strong style={{ color: 'var(--text-primary)' }}>{evaluatedCount}</strong> / {totalQuestions} Questions
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              {/* Score pill */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 14px',
                  borderRadius: 'var(--radius-full)',
                  background:
                    evaluatedCount === 0
                      ? 'rgba(255, 255, 255, 0.05)'
                      : totalScoreAwarded / (evaluatedCount * 2) >= 0.75
                      ? 'rgba(16, 185, 129, 0.15)'
                      : totalScoreAwarded / (evaluatedCount * 2) >= 0.5
                      ? 'rgba(245, 158, 11, 0.15)'
                      : 'rgba(239, 68, 68, 0.15)',
                  border: `1px solid ${
                    evaluatedCount === 0
                      ? 'var(--border-subtle)'
                      : totalScoreAwarded / (evaluatedCount * 2) >= 0.75
                      ? 'rgba(16, 185, 129, 0.4)'
                      : totalScoreAwarded / (evaluatedCount * 2) >= 0.5
                      ? 'rgba(245, 158, 11, 0.4)'
                      : 'rgba(239, 68, 68, 0.4)'
                  }`,
                }}
              >
                <Award size={16} color="#fbbf24" />
                <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Score: {totalScoreAwarded} / {evaluatedCount > 0 ? evaluatedCount * 2 : maxPossibleMarks}
                </span>
              </div>

              {/* Evaluate All button */}
              <button
                type="button"
                onClick={handleEvaluateAll}
                disabled={isEvaluatingAll}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-primary)',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: isEvaluatingAll ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                {isEvaluatingAll ? <Loader2 size={14} className="spin" /> : <Send size={14} />}
                <span>Evaluate All</span>
              </button>
            </div>
          </div>

          {/* Question List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {testDeck.questions.map((q, idx) => {
              const evaluation = evaluations[q.question_id];
              const isEvaluating = !!evaluatingMap[q.question_id];
              const isModelAnswerOpen = !!expandedModelAnswers[q.question_id];
              const answerText = studentAnswers[q.question_id] || '';

              return (
                <div
                  key={q.question_id || idx}
                  style={{
                    background: 'var(--bg-card)',
                    border: evaluation
                      ? evaluation.score_awarded === 2
                        ? '1px solid rgba(16, 185, 129, 0.4)'
                        : evaluation.score_awarded === 1
                        ? '1px solid rgba(245, 158, 11, 0.4)'
                        : '1px solid rgba(239, 68, 68, 0.4)'
                      : '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '24px',
                    boxShadow: 'var(--shadow-card)',
                    transition: 'all 0.25s ease',
                  }}
                >
                  {/* Question Header */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span
                        style={{
                          fontSize: '12px',
                          fontWeight: 800,
                          padding: '3px 10px',
                          borderRadius: 'var(--radius-sm)',
                          background: 'var(--primary)',
                          color: '#ffffff',
                        }}
                      >
                        {q.question_id || `Q${idx + 1}`}
                      </span>
                      <span
                        style={{
                          fontSize: '12px',
                          fontWeight: 600,
                          color: 'var(--text-muted)',
                        }}
                      >
                        Part-A | 2 Marks
                      </span>
                    </div>

                    {/* Evaluation status pill */}
                    {evaluation && (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '13px',
                          fontWeight: 700,
                          padding: '4px 12px',
                          borderRadius: 'var(--radius-full)',
                          background:
                            evaluation.score_awarded === 2
                              ? 'rgba(16, 185, 129, 0.2)'
                              : evaluation.score_awarded === 1
                              ? 'rgba(245, 158, 11, 0.2)'
                              : 'rgba(239, 68, 68, 0.2)',
                          color:
                            evaluation.score_awarded === 2
                              ? '#34d399'
                              : evaluation.score_awarded === 1
                              ? '#fbbf24'
                              : '#f87171',
                          border: `1px solid ${
                            evaluation.score_awarded === 2
                              ? '#10b981'
                              : evaluation.score_awarded === 1
                              ? '#f59e0b'
                              : '#ef4444'
                          }`,
                        }}
                      >
                        {evaluation.score_awarded === 2 ? (
                          <CheckCircle2 size={14} />
                        ) : evaluation.score_awarded === 1 ? (
                          <Info size={14} />
                        ) : (
                          <XCircle size={14} />
                        )}
                        Score: {evaluation.score_awarded} / 2 Marks
                      </span>
                    )}
                  </div>

                  {/* Question Prompt */}
                  <h4
                    style={{
                      fontSize: '16px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      lineHeight: '1.5',
                      marginBottom: '16px',
                    }}
                  >
                    {q.question}
                  </h4>

                  {/* Student Answer Textarea */}
                  <div style={{ marginBottom: '16px' }}>
                    <textarea
                      value={answerText}
                      onChange={(e) =>
                        setStudentAnswers((prev) => ({
                          ...prev,
                          [q.question_id]: e.target.value,
                        }))
                      }
                      disabled={isEvaluating}
                      placeholder="Write your concise, technical definition or trade-off answer (2-3 sentences)..."
                      rows={3}
                      style={{
                        width: '100%',
                        padding: '12px 14px',
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-subtle)',
                        color: 'var(--text-primary)',
                        fontSize: '14px',
                        fontFamily: 'inherit',
                        lineHeight: 1.5,
                        resize: 'vertical',
                        outline: 'none',
                      }}
                    />
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginTop: '6px',
                      }}
                    >
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {answerText.length} characters
                      </span>
                      <button
                        type="button"
                        onClick={() => handleEvaluateQuestion(q)}
                        disabled={isEvaluating || !answerText.trim()}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '6px 14px',
                          borderRadius: 'var(--radius-sm)',
                          border: 'none',
                          background: evaluation ? 'var(--bg-tertiary)' : 'var(--primary)',
                          color: '#ffffff',
                          fontWeight: 600,
                          fontSize: '12px',
                          cursor: isEvaluating || !answerText.trim() ? 'not-allowed' : 'pointer',
                          opacity: isEvaluating || !answerText.trim() ? 0.5 : 1,
                          transition: 'all 0.2s ease',
                        }}
                      >
                        {isEvaluating ? (
                          <>
                            <Loader2 size={12} className="spin" />
                            <span>Grading...</span>
                          </>
                        ) : (
                          <>
                            <Send size={12} />
                            <span>{evaluation ? 'Re-Evaluate Answer' : 'Evaluate Answer'}</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Semantic Evaluation Card */}
                  {evaluation && (
                    <div
                      style={{
                        background: 'rgba(15, 23, 42, 0.75)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        padding: '16px',
                        marginBottom: '14px',
                      }}
                    >
                      {/* Rubric Points Covered & Missed */}
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                          gap: '12px',
                          marginBottom: '14px',
                        }}
                      >
                        {/* Points Covered */}
                        <div
                          style={{
                            background: 'rgba(16, 185, 129, 0.08)',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '10px 12px',
                          }}
                        >
                          <div
                            style={{
                              fontSize: '12px',
                              fontWeight: 700,
                              color: '#34d399',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              marginBottom: '6px',
                            }}
                          >
                            <CheckCircle2 size={14} />
                            <span>Rubric Points Addressed (+1 Mark each):</span>
                          </div>
                          {evaluation.points_covered && evaluation.points_covered.length > 0 ? (
                            <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '13px', color: '#d1fae5' }}>
                              {evaluation.points_covered.map((pt, pIdx) => (
                                <li key={pIdx} style={{ marginBottom: '2px' }}>{pt}</li>
                              ))}
                            </ul>
                          ) : (
                            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                              None identified in your response.
                            </span>
                          )}
                        </div>

                        {/* Points Missed */}
                        <div
                          style={{
                            background: 'rgba(239, 68, 68, 0.08)',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '10px 12px',
                          }}
                        >
                          <div
                            style={{
                              fontSize: '12px',
                              fontWeight: 700,
                              color: '#f87171',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              marginBottom: '6px',
                            }}
                          >
                            <XCircle size={14} />
                            <span>Rubric Points Missed / Incomplete:</span>
                          </div>
                          {evaluation.points_missed && evaluation.points_missed.length > 0 ? (
                            <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '13px', color: '#fee2e2' }}>
                              {evaluation.points_missed.map((pt, pIdx) => (
                                <li key={pIdx} style={{ marginBottom: '2px' }}>{pt}</li>
                              ))}
                            </ul>
                          ) : (
                            <span style={{ fontSize: '12px', color: '#34d399', fontStyle: 'italic' }}>
                              All required concepts were adequately covered!
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Constructive Feedback */}
                      {evaluation.feedback && (
                        <div
                          style={{
                            background: 'rgba(99, 102, 241, 0.08)',
                            border: '1px solid rgba(99, 102, 241, 0.2)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '10px 12px',
                            fontSize: '13px',
                            color: '#e0e7ff',
                            lineHeight: 1.5,
                          }}
                        >
                          <strong style={{ color: '#a5b4fc' }}>Evaluator Feedback: </strong>
                          {evaluation.feedback}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Expandable Model Answer Accordion */}
                  <div
                    style={{
                      borderTop: '1px solid var(--border-subtle)',
                      paddingTop: '12px',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => toggleModelAnswer(q.question_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        width: '100%',
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-secondary)',
                        fontSize: '13px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        padding: '4px 0',
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <HelpCircle size={14} color="#818cf8" />
                        <span>Reference Model Answer & Criteria</span>
                      </span>
                      {isModelAnswerOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>

                    {isModelAnswerOpen && (
                      <div
                        style={{
                          marginTop: '10px',
                          padding: '12px 14px',
                          background: 'rgba(30, 41, 59, 0.5)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                          fontSize: '13px',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        <div style={{ marginBottom: '8px' }}>
                          <strong style={{ color: 'var(--text-primary)' }}>Ideal Model Answer: </strong>
                          <span>{q.model_answer}</span>
                        </div>
                        {q.key_points && q.key_points.length > 0 && (
                          <div>
                            <strong style={{ color: 'var(--text-primary)' }}>Key Rubric Points (1 Mark each): </strong>
                            <ol style={{ paddingLeft: '18px', marginTop: '4px' }}>
                              {q.key_points.map((pt, ptIdx) => (
                                <li key={ptIdx} style={{ color: 'var(--text-secondary)' }}>{pt}</li>
                              ))}
                            </ol>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
