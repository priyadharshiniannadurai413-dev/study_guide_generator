/**
 * src/pages/QuizPage.jsx
 * Interactive MCQ Quiz Arena with instant feedback, explanations, and confetti score review.
 */

import React, { useState, useEffect } from 'react';
import confetti from 'canvas-confetti';
import {
  HelpCircle,
  Sparkles,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Trophy,
  ArrowRight,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Award,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { DocumentSelector } from '../components/DocumentSelector';
import { useToast } from '../context/ToastContext';

export function QuizPage({ initialDocId = 'syllabus' }) {
  const [selectedDocId, setSelectedDocId] = useState(initialDocId);
  const [questionCount, setQuestionCount] = useState(5);
  const [focusTopic, setFocusTopic] = useState('');
  const [quizDeck, setQuizDeck] = useState(null);
  const [loading, setLoading] = useState(false);

  // Gameplay state
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState({}); // { [questionIdx]: selectedOptionIdx }
  const [isFinished, setIsFinished] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    if (initialDocId) {
      setSelectedDocId(initialDocId);
    }
  }, [initialDocId]);

  const handleGenerateQuiz = async (e) => {
    if (e) e.preventDefault();
    if (!selectedDocId) {
      addToast('Please select a knowledge source.', 'warning');
      return;
    }

    try {
      setLoading(true);
      const deck = await endpoints.generateMCQs({
        docId: selectedDocId,
        count: questionCount,
        topic: focusTopic.trim() || undefined,
      });

      if (!deck?.questions || deck.questions.length === 0) {
        throw new Error('No quiz questions generated. Please try again.');
      }

      setQuizDeck(deck);
      setCurrentIndex(0);
      setUserAnswers({});
      setIsFinished(false);
      addToast(`Generated ${deck.questions.length} question quiz!`, 'success');
    } catch (err) {
      console.error('Quiz generation failed:', err);
      addToast(`Failed to generate quiz: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectOption = (optionIndex) => {
    // If already answered this question, do not allow changing
    if (userAnswers[currentIndex] !== undefined) return;

    const newAnswers = { ...userAnswers, [currentIndex]: optionIndex };
    setUserAnswers(newAnswers);

    // If this was the last question, calculate score and launch confetti if good score
    if (Object.keys(newAnswers).length === quizDeck.questions.length) {
      const correctCount = quizDeck.questions.reduce((acc, q, idx) => {
        return newAnswers[idx] === q.correct_index ? acc + 1 : acc;
      }, 0);

      const percent = Math.round((correctCount / quizDeck.questions.length) * 100);
      if (percent >= 60) {
        try {
          confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.6 },
          });
        } catch {}
      }
      setIsFinished(true);
    }
  };

  const calculateScore = () => {
    if (!quizDeck) return { correct: 0, total: 0, percent: 0 };
    const correct = quizDeck.questions.reduce((acc, q, idx) => {
      return userAnswers[idx] === q.correct_index ? acc + 1 : acc;
    }, 0);
    const total = quizDeck.questions.length;
    const percent = Math.round((correct / total) * 100);
    return { correct, total, percent };
  };

  const optionLabels = ['A', 'B', 'C', 'D'];

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ marginBottom: '8px' }}>Interactive MCQ Arena</h1>
        <p style={{ fontSize: '1.05rem' }}>
          Evaluate your understanding with AI-generated 4-option multiple-choice quizzes, instant
          answer verification, and in-depth conceptual explanations.
        </p>
      </div>

      {/* Quiz Setup Card */}
      {!quizDeck && (
        <form
          onSubmit={handleGenerateQuiz}
          className="glass-card"
          style={{ padding: '28px', marginBottom: '32px' }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '20px',
              marginBottom: '24px',
            }}
          >
            <DocumentSelector
              selectedDocId={selectedDocId}
              onSelectDocId={setSelectedDocId}
            />

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                }}
              >
                Number of Questions: {questionCount}
              </label>
              <input
                type="range"
                min="1"
                max="20"
                value={questionCount}
                onChange={(e) => setQuestionCount(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary)', cursor: 'pointer' }}
              />
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  marginTop: '4px',
                }}
              >
                <span>1 MCQ</span>
                <span>5 MCQs</span>
                <span>10 MCQs</span>
                <span>20 MCQs</span>
              </div>
            </div>

            <div style={{ gridColumn: '1 / -1' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                }}
              >
                Focus Topic / Sub-Chapter (Optional):
              </label>
              <input
                type="text"
                value={focusTopic}
                onChange={(e) => setFocusTopic(e.target.value)}
                placeholder="e.g., Op-Amp Slew Rate, Feedback Oscillators, Differential Amplifiers"
                className="input"
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ padding: '12px 28px' }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Generating MCQs...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Generate Quiz Arena</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {loading && (
        <div className="glass-card" style={{ padding: '60px', textAlign: 'center' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
          <h3 style={{ marginBottom: '8px' }}>Crafting Academic Questions & Explanations...</h3>
          <p style={{ color: 'var(--text-muted)' }}>
            Gemini is formulating 4 distinct options with pedagogical distractor rationales.
          </p>
        </div>
      )}

      {/* Quiz Gameplay Card */}
      {quizDeck && (
        <div>
          {/* Progress & Control Bar */}
          <div
            className="glass-card"
            style={{
              padding: '16px 22px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {quizDeck.title || 'Knowledge Assessment'}
              </div>
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>
                Question {currentIndex + 1} of {quizDeck.questions.length}
              </div>
            </div>

            {/* Answered Counter */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                className="badge badge-primary"
                style={{ fontSize: '0.8rem', padding: '6px 12px' }}
              >
                Answered: {Object.keys(userAnswers).length}/{quizDeck.questions.length}
              </div>

              <button
                onClick={() => {
                  if (window.confirm('Reset current quiz?')) {
                    setQuizDeck(null);
                    setUserAnswers({});
                    setIsFinished(false);
                  }
                }}
                className="btn btn-ghost btn-sm"
                title="New Quiz Setup"
              >
                <RotateCcw size={14} />
                <span>Reset</span>
              </button>
            </div>
          </div>

          {/* Active Question Box */}
          {quizDeck.questions[currentIndex] && (
            <div className="glass-card" style={{ padding: '32px', marginBottom: '20px' }}>
              <h3
                style={{
                  fontSize: '1.2rem',
                  lineHeight: 1.5,
                  marginBottom: '24px',
                  fontWeight: 600,
                }}
              >
                {quizDeck.questions[currentIndex].question}
              </h3>

              {/* 4 Options Grid */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {quizDeck.questions[currentIndex].options.map((optionText, optIdx) => {
                  const isSelected = userAnswers[currentIndex] === optIdx;
                  const hasAnswered = userAnswers[currentIndex] !== undefined;
                  const isCorrect = optIdx === quizDeck.questions[currentIndex].correct_index;

                  let borderClr = 'var(--border-subtle)';
                  let bgClr = 'rgba(255, 255, 255, 0.03)';
                  let textClr = 'var(--text-primary)';

                  if (hasAnswered) {
                    if (isCorrect) {
                      borderClr = 'var(--success)';
                      bgClr = 'rgba(16, 185, 129, 0.15)';
                      textClr = '#6ee7b7';
                    } else if (isSelected) {
                      borderClr = 'var(--error)';
                      bgClr = 'rgba(239, 68, 68, 0.15)';
                      textClr = '#fca5a5';
                    }
                  } else if (isSelected) {
                    borderClr = 'var(--primary)';
                    bgClr = 'rgba(99, 102, 241, 0.12)';
                  }

                  return (
                    <button
                      key={optIdx}
                      type="button"
                      onClick={() => handleSelectOption(optIdx)}
                      disabled={hasAnswered}
                      style={{
                        padding: '16px 20px',
                        background: bgClr,
                        border: `1px solid ${borderClr}`,
                        borderRadius: 'var(--radius-md)',
                        textAlign: 'left',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '14px',
                        cursor: hasAnswered ? 'default' : 'pointer',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <span
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: 'var(--radius-sm)',
                          background: isSelected || (hasAnswered && isCorrect)
                            ? 'rgba(255, 255, 255, 0.12)'
                            : 'rgba(255, 255, 255, 0.05)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontSize: '0.88rem',
                          color: textClr,
                          flexShrink: 0,
                        }}
                      >
                        {optionLabels[optIdx]}
                      </span>

                      <span style={{ flex: 1, fontSize: '0.96rem', color: textClr }}>
                        {optionText}
                      </span>

                      {hasAnswered && isCorrect && (
                        <CheckCircle2 size={20} color="var(--success)" />
                      )}
                      {hasAnswered && isSelected && !isCorrect && (
                        <XCircle size={20} color="var(--error)" />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Explanation Card upon Answer */}
              {userAnswers[currentIndex] !== undefined && (
                <div
                  style={{
                    marginTop: '24px',
                    padding: '18px 22px',
                    background: 'rgba(99, 102, 241, 0.08)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-accent)',
                    animation: 'fadeIn 0.3s ease',
                  }}
                >
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: '0.88rem',
                      color: '#a5b4fc',
                      marginBottom: '6px',
                    }}
                  >
                    Explanation:
                  </div>
                  <p style={{ fontSize: '0.94rem', lineHeight: 1.6, color: 'var(--text-primary)' }}>
                    {quizDeck.questions[currentIndex].explanation}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Navigation Controls */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <button
              onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
              disabled={currentIndex === 0}
              className="btn btn-secondary btn-sm"
            >
              <ChevronLeft size={16} />
              <span>Previous</span>
            </button>

            {currentIndex < quizDeck.questions.length - 1 ? (
              <button
                onClick={() => setCurrentIndex((prev) => prev + 1)}
                className="btn btn-primary btn-sm"
              >
                <span>Next Question</span>
                <ChevronRight size={16} />
              </button>
            ) : (
              <button
                onClick={() => setIsFinished(true)}
                className="btn btn-primary btn-sm"
              >
                <span>View Final Score</span>
                <Trophy size={16} />
              </button>
            )}
          </div>

          {/* Finished Score Report Modal */}
          {isFinished && (
            <div className="modal-overlay" onClick={() => setIsFinished(false)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div style={{ textAlign: 'center', padding: '10px 0' }}>
                  <div
                    style={{
                      width: '64px',
                      height: '64px',
                      borderRadius: 'var(--radius-full)',
                      background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 16px auto',
                      color: '#ffffff',
                      boxShadow: '0 0 24px var(--primary-glow)',
                    }}
                  >
                    <Trophy size={32} />
                  </div>

                  <h2 style={{ marginBottom: '8px' }}>Quiz Completed!</h2>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>
                    {quizDeck.title || 'Academic Concept Review'}
                  </p>

                  {(() => {
                    const { correct, total, percent } = calculateScore();
                    return (
                      <div
                        style={{
                          background: 'rgba(255, 255, 255, 0.04)',
                          borderRadius: 'var(--radius-lg)',
                          padding: '24px',
                          marginBottom: '24px',
                        }}
                      >
                        <div style={{ fontSize: '3rem', fontWeight: 800, color: 'var(--cyan)' }}>
                          {percent}%
                        </div>
                        <div style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>
                          You got <strong>{correct}</strong> out of <strong>{total}</strong> correct
                        </div>
                      </div>
                    );
                  })()}

                  <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                    <button
                      onClick={() => {
                        setUserAnswers({});
                        setCurrentIndex(0);
                        setIsFinished(false);
                      }}
                      className="btn btn-secondary"
                    >
                      <RotateCcw size={15} />
                      <span>Retake Quiz</span>
                    </button>
                    <button
                      onClick={() => {
                        setQuizDeck(null);
                        setUserAnswers({});
                        setIsFinished(false);
                      }}
                      className="btn btn-primary"
                    >
                      <span>New Quiz</span>
                      <ArrowRight size={15} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
