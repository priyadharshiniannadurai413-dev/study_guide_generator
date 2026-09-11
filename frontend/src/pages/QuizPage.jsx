/**
 * src/pages/QuizPage.jsx
 * Interactive MCQ Quiz Arena with instant feedback, explanations, and confetti score review.
 */

import React, { useState, useEffect, useRef } from 'react';
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
  Globe,
  Minus,
  Plus,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { DocumentSelector } from '../components/DocumentSelector';
import { useToast } from '../context/ToastContext';
import { MCQArena } from '../components/study/MCQArena';

export function QuizPage({ initialDocId = 'syllabus' }) {
  const [selectedDocId, setSelectedDocId] = useState(initialDocId);
  const [webUrl, setWebUrl] = useState('');
  const [questionCount, setQuestionCount] = useState(20);
  const [difficulty, setDifficulty] = useState('intermediate');
  const [enableWeb, setEnableWeb] = useState(() => {
    return localStorage.getItem('studysync_mcp_fetch_auto_enrich') === 'true';
  });
  const [focusTopic, setFocusTopic] = useState('');
  const [quizDeck, setQuizDeck] = useState(null);
  const [loading, setLoading] = useState(false);
  const [genProgress, setGenProgress] = useState(0);
  const [genStatusText, setGenStatusText] = useState('');
  const genIntervalRef = useRef(null);

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

  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      if (genIntervalRef.current) clearInterval(genIntervalRef.current);
    };
  }, []);

  const handleGenerateQuiz = async (e) => {
    if (e) e.preventDefault();
    if (!selectedDocId && !webUrl.trim()) {
      addToast('Please select a knowledge source document or provide a web URL.', 'warning');
      return;
    }

    try {
      setLoading(true);
      setGenProgress(14);
      setGenStatusText(
        webUrl.trim()
          ? 'Connecting to Fetch MCP & retrieving webpage...'
          : 'Querying vector embeddings & analyzing syllabus scope...'
      );

      let current = 14;
      if (genIntervalRef.current) clearInterval(genIntervalRef.current);
      genIntervalRef.current = setInterval(() => {
        current += Math.floor(Math.random() * 8) + 4;
        if (current > 92) current = 92;
        setGenProgress(current);

        if (current >= 35 && current < 65) {
          setGenStatusText(
            webUrl.trim()
              ? 'Parsing article structure & extracting core technical content...'
              : 'Synthesizing question stems & calibrating depth...'
          );
        } else if (current >= 65 && current < 88) {
          setGenStatusText('Formulating distractor options & pedagogical rationales...');
        } else if (current >= 88) {
          setGenStatusText('Validating answer keys and formatting quiz deck...');
        }
      }, 350);

      const deck = await endpoints.generateMCQs({
        docId: selectedDocId || undefined,
        url: webUrl.trim() || undefined,
        count: questionCount,
        topic: focusTopic.trim() || undefined,
        difficulty,
        enableWeb: Boolean(enableWeb || webUrl.trim()),
      });

      if (genIntervalRef.current) clearInterval(genIntervalRef.current);
      setGenProgress(100);
      setGenStatusText('Quiz arena generated successfully!');
      await new Promise((r) => setTimeout(r, 450));

      if (!deck?.questions || deck.questions.length === 0) {
        throw new Error('No quiz questions generated. Please try again.');
      }

      setQuizDeck(deck);
      setCurrentIndex(0);
      setUserAnswers({});
      setIsFinished(false);
      addToast(`Generated ${deck.questions.length} question quiz arena!`, 'success');
    } catch (err) {
      if (genIntervalRef.current) clearInterval(genIntervalRef.current);
      console.error('Quiz generation failed:', err);
      addToast(`Failed to generate quiz: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectOption = (optionIndex) => {
    if (userAnswers[currentIndex] !== undefined) return;

    const newAnswers = { ...userAnswers, [currentIndex]: optionIndex };
    setUserAnswers(newAnswers);

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

            {/* Redesigned Question Count Selector: Presets + Stepper */}
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '8px',
                }}
              >
                <label
                  style={{
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                  }}
                >
                  Number of Questions
                </label>
                <span
                  style={{
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '6px',
                    background: 'rgba(99, 102, 241, 0.2)',
                    color: '#818cf8',
                    border: '1px solid rgba(99, 102, 241, 0.3)',
                  }}
                >
                  {questionCount} {questionCount === 1 ? 'Question' : 'Questions'}
                </span>
              </div>

              {/* Quick Preset Pills */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(5, 1fr)',
                  gap: '6px',
                  marginBottom: '10px',
                }}
              >
                {[1, 5, 10, 15, 20].map((num) => {
                  const isSelected = questionCount === num;
                  return (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setQuestionCount(num)}
                      style={{
                        padding: '6px 0',
                        borderRadius: '8px',
                        fontSize: '0.84rem',
                        fontWeight: 600,
                        textAlign: 'center',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        border: isSelected
                          ? '1.5px solid var(--primary)'
                          : '1px solid var(--border-subtle)',
                        background: isSelected
                          ? 'rgba(99, 102, 241, 0.25)'
                          : 'rgba(255, 255, 255, 0.03)',
                        color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                      }}
                    >
                      {num}
                    </button>
                  );
                })}
              </div>

              {/* Custom Stepper Controls */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '10px',
                  padding: '4px 6px',
                }}
              >
                <button
                  type="button"
                  onClick={() => setQuestionCount((c) => Math.max(1, c - 1))}
                  disabled={questionCount <= 1}
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: questionCount <= 1 ? 'var(--text-muted)' : 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: questionCount <= 1 ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  title="Decrease count"
                >
                  <Minus size={14} />
                </button>

                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={questionCount}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      if (!isNaN(val)) {
                        setQuestionCount(Math.min(20, Math.max(1, val)));
                      }
                    }}
                    style={{
                      width: '60px',
                      textAlign: 'center',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-primary)',
                      fontSize: '1rem',
                      fontWeight: 700,
                      outline: 'none',
                    }}
                  />
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>/ 20 max</span>
                </div>

                <button
                  type="button"
                  onClick={() => setQuestionCount((c) => Math.min(20, c + 1))}
                  disabled={questionCount >= 20}
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: questionCount >= 20 ? 'var(--text-muted)' : 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: questionCount >= 20 ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  title="Increase count"
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>

            {/* Web URL (Fetch MCP Integration) */}
            <div style={{ gridColumn: '1 / -1' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '6px',
                }}
              >
                <label
                  style={{
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <Globe size={14} color="#38bdf8" />
                  <span>Web Documentation URL (Fetch MCP Web Extraction — Optional)</span>
                </label>
                <span
                  style={{
                    fontSize: '0.72rem',
                    background: 'rgba(56, 189, 248, 0.15)',
                    color: '#38bdf8',
                    padding: '2px 8px',
                    borderRadius: '6px',
                    fontWeight: 600,
                  }}
                >
                  MCP Tool Enabled
                </span>
              </div>
              <input
                type="url"
                value={webUrl}
                onChange={(e) => setWebUrl(e.target.value)}
                placeholder="https://en.wikipedia.org/wiki/Static_random-access_memory or official docs"
                className="input"
                style={{ width: '100%' }}
              />
              <p
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  marginTop: '4px',
                  lineHeight: 1.4,
                }}
              >
                When provided, Fetch MCP retrieves the live page, cleans boilerplate/navigation, and
                grounds MCQs directly in the web article context.
              </p>
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

            <div style={{ gridColumn: '1 / -1' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '8px',
                }}
              >
                Question Difficulty & Cognitive Depth:
              </label>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '10px',
                }}
              >
                {[
                  {
                    id: 'beginner',
                    label: 'Beginner',
                    badge: 'Recall & Terms',
                    desc: 'Direct definitions, syntax recognition, distinct choices',
                  },
                  {
                    id: 'intermediate',
                    label: 'Intermediate',
                    badge: 'Reasoning & Debug',
                    desc: 'Code tracing, operational trade-offs, common bug patterns',
                  },
                  {
                    id: 'advanced',
                    label: 'Advanced',
                    badge: 'Edge Cases & Rigor',
                    desc: 'Multi-step scenario analysis, failure modes, subtle traps',
                  },
                ].map((tier) => {
                  const active = difficulty === tier.id;
                  return (
                    <button
                      key={tier.id}
                      type="button"
                      onClick={() => setDifficulty(tier.id)}
                      style={{
                        padding: '12px 14px',
                        borderRadius: '10px',
                        border: active ? '1.5px solid var(--primary)' : '1px solid var(--border-subtle)',
                        background: active ? 'rgba(99, 102, 241, 0.16)' : 'rgba(255, 255, 255, 0.02)',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.2s ease',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span
                          style={{
                            fontWeight: 700,
                            fontSize: '0.92rem',
                            color: active ? '#818cf8' : 'var(--text-primary)',
                          }}
                        >
                          {tier.label}
                        </span>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            padding: '2px 8px',
                            borderRadius: '999px',
                            background: active ? 'rgba(99, 102, 241, 0.3)' : 'rgba(255, 255, 255, 0.06)',
                            color: active ? '#c7d2fe' : 'var(--text-muted)',
                          }}
                        >
                          {tier.badge}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                        {tier.desc}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Research Source Selector: Uploaded Documents vs Uploaded Documents + Fetch MCP */}
            <div style={{ marginTop: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.86rem', fontWeight: 600 }}>
                Evidence & Knowledge Sources
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setEnableWeb(false)}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '10px',
                    border: !enableWeb ? '1.5px solid var(--primary)' : '1px solid var(--border-subtle)',
                    background: !enableWeb ? 'rgba(99, 102, 241, 0.16)' : 'rgba(255, 255, 255, 0.02)',
                    color: !enableWeb ? '#ffffff' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.18s ease',
                  }}
                >
                  <span>📄</span>
                  <span>Uploaded Documents Only</span>
                </button>
                <button
                  type="button"
                  onClick={() => setEnableWeb(true)}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '10px',
                    border: enableWeb ? '1.5px solid #3b82f6' : '1px solid var(--border-subtle)',
                    background: enableWeb ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.02)',
                    color: enableWeb ? '#ffffff' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.18s ease',
                  }}
                >
                  <span>🌐</span>
                  <span>Documents + Fetch MCP Web</span>
                </button>
              </div>
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
                  <span>Generating MCQs ({genProgress}%)...</span>
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

      {/* Multi-Stage Loading Progress Bar Card */}
      {loading && (
        <div
          className="glass-card"
          style={{
            padding: '36px 32px',
            marginBottom: '32px',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.9) 100%)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Loader2 size={20} style={{ animation: 'spin 1.2s linear infinite', color: '#818cf8' }} />
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
                Synthesizing Question Deck
              </h3>
            </div>
            <span
              style={{
                fontFamily: 'monospace',
                fontSize: '0.92rem',
                fontWeight: 700,
                color: '#818cf8',
                background: 'rgba(99, 102, 241, 0.15)',
                padding: '3px 10px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
              }}
            >
              {genProgress}%
            </span>
          </div>

          {/* Progress Track */}
          <div
            style={{
              width: '100%',
              height: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              borderRadius: '999px',
              overflow: 'hidden',
              marginBottom: '14px',
            }}
          >
            <div
              style={{
                width: `${genProgress}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #6366f1 0%, #38bdf8 50%, #818cf8 100%)',
                borderRadius: '999px',
                transition: 'width 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
                boxShadow: '0 0 12px rgba(99, 102, 241, 0.5)',
              }}
            />
          </div>

          {/* Dynamic Status Text */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.84rem', color: '#cbd5e1', fontWeight: 500 }}>
              {genStatusText || 'Calibrating assessment depth...'}
            </span>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} Tier • {questionCount} MCQs
            </span>
          </div>
        </div>
      )}

      {/* Quiz Gameplay: Deferred-Grading Exam Simulator */}
      {quizDeck && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
            <button
              onClick={() => {
                if (window.confirm('Leave current exam and return to quiz setup?')) {
                  setQuizDeck(null);
                }
              }}
              className="btn btn-secondary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <RotateCcw size={14} />
              <span>New Exam Setup</span>
            </button>
          </div>
          <MCQArena
            questions={quizDeck.questions.map((q) => ({
              question: q.question,
              options: q.options,
              correct_answer:
                q.correct_answer ||
                (typeof q.correct_index === 'number' && q.options && q.options[q.correct_index]) ||
                '',
              explanation: q.explanation || '',
            }))}
            topic={focusTopic.trim() || quizDeck.title || 'MCQ Knowledge Assessment'}
          />
        </div>
      )}
    </div>
  );
}
