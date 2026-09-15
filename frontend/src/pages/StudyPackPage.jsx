/**
 * src/pages/StudyPackPage.jsx
 * Complete Study Pack Studio:
 * - Lecture PDF upload or raw syllabus/lecture text paste
 * - Calibrated difficulty selector (Beginner, Intermediate, Advanced)
 * - Concise summary notes
 * - 20 practice MCQs with interactive quiz engine & detailed explanations
 * - 5 short-answer questions with model answers & grading rubrics
 * - Key terms glossary with real-time search
 * - Suggested study progression roadmap
 * - One-click export to ReportLab PDF and Anki/Quizlet CSV
 */

import React, { useState, useEffect, useMemo, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import confetti from 'canvas-confetti';
import {
  Sparkles,
  Upload,
  FileText,
  BookOpen,
  HelpCircle,
  Download,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Search,
  Layers,
  ChevronRight,
  Eye,
  EyeOff,
  Copy,
  Check,
  Award,
  BarChart3,
  FileSpreadsheet,
  FileCheck,
  AlertCircle,
  Loader2,
  Clock,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { useToast } from '../context/ToastContext';

export function StudyPackPage({ initialDocId = 'syllabus' }) {
  const { addToast } = useToast();

  // Input state
  const [inputMode, setInputMode] = useState('upload'); // 'upload' | 'paste' | 'existing'
  const [file, setFile] = useState(null);
  const [pastedText, setPastedText] = useState('');
  const [selectedDocId, setSelectedDocId] = useState(initialDocId);
  const [availableDocs, setAvailableDocs] = useState([]);
  const [difficulty, setDifficulty] = useState('intermediate'); // 'beginner' | 'intermediate' | 'advanced'

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [studyPack, setStudyPack] = useState(null);
  const [activePackTab, setActivePackTab] = useState('roadmap'); // 'roadmap' | 'summary' | 'mcq' | 'short_answers' | 'glossary'

  // Interactive Quiz state
  const [userAnswers, setUserAnswers] = useState({}); // { [qIndex]: optionIndex }
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState(0);

  // Short Answer state
  const [revealedAnswers, setRevealedAnswers] = useState({}); // { [saIndex]: boolean }

  // Glossary search state
  const [glossaryQuery, setGlossaryQuery] = useState('');

  // Export loaders
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingCsv, setDownloadingCsv] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);

  // Drag-and-drop
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Load existing documents for dropdown
  useEffect(() => {
    let isMounted = true;
    endpoints
      .listDocuments()
      .then((docs) => {
        if (isMounted && Array.isArray(docs)) {
          setAvailableDocs(docs);
        }
      })
      .catch((err) => {
        console.warn('Failed to load documents for study pack:', err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Handle PDF file selection
  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith('.pdf')) {
      addToast('Only PDF documents are supported.', 'error');
      return;
    }
    setFile(selected);
    addToast(`Selected "${selected.name}" (${(selected.size / 1024).toFixed(1)} KB)`, 'info');
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped && dropped.name.toLowerCase().endsWith('.pdf')) {
      setFile(dropped);
      addToast(`Selected "${dropped.name}"`, 'info');
    } else {
      addToast('Please drop a valid .pdf document.', 'error');
    }
  };

  // Generate Study Pack
  const handleGenerate = async () => {
    if (inputMode === 'upload' && !file) {
      addToast('Please select or upload a lecture PDF.', 'warning');
      return;
    }
    if (inputMode === 'paste' && !pastedText.trim()) {
      addToast('Please paste your syllabus content or lecture notes.', 'warning');
      return;
    }

    try {
      setIsGenerating(true);
      setStudyPack(null);
      setUserAnswers({});
      setQuizSubmitted(false);
      setRevealedAnswers({});
      addToast(`Generating calibrated ${difficulty.toUpperCase()} Study Pack...`, 'info');

      let result = null;
      if (inputMode === 'upload' && file) {
        result = await endpoints.uploadAndGenerateStudyPack(file, difficulty);
      } else if (inputMode === 'paste') {
        result = await endpoints.generateStudyPack({
          pastedText: pastedText.trim(),
          difficulty,
        });
      } else {
        result = await endpoints.generateStudyPack({
          docId: selectedDocId,
          difficulty,
        });
      }

      if (!result) {
        throw new Error('Received empty response from study pack engine.');
      }

      setStudyPack(result);
      setActivePackTab('roadmap');
      addToast('Complete Study Pack generated successfully!', 'success');

      try {
        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.7 },
        });
      } catch {
        // non-blocking
      }
    } catch (err) {
      console.error('Study pack generation failed:', err);
      addToast(`Generation failed: ${err.message || 'Server error'}`, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  // Quiz submission & scoring
  const handleOptionSelect = (qIdx, optIdx) => {
    if (quizSubmitted) return;
    setUserAnswers((prev) => ({ ...prev, [qIdx]: optIdx }));
  };

  const handleQuizSubmit = () => {
    if (!studyPack?.mcqs?.length) return;
    let correctCount = 0;
    studyPack.mcqs.forEach((mcq, idx) => {
      const chosen = userAnswers[idx];
      // Compare chosen index with correct_index or correct_answer text
      const isCorrect =
        chosen !== undefined &&
        (chosen === mcq.correct_index ||
          (mcq.correct_answer && mcq.options?.[chosen] === mcq.correct_answer));
      if (isCorrect) correctCount++;
    });

    setQuizScore(correctCount);
    setQuizSubmitted(true);

    const percent = Math.round((correctCount / studyPack.mcqs.length) * 100);
    if (percent >= 80) {
      addToast(`Outstanding! Score: ${correctCount}/${studyPack.mcqs.length} (${percent}%)`, 'success');
      try {
        confetti({ particleCount: 80, spread: 80, origin: { y: 0.6 } });
      } catch {
        // non-blocking
      }
    } else {
      addToast(`Quiz complete: ${correctCount}/${studyPack.mcqs.length} (${percent}%)`, 'info');
    }
  };

  const handleQuizReset = () => {
    setUserAnswers({});
    setQuizSubmitted(false);
    setQuizScore(0);
    addToast('Quiz reset. Ready for re-testing!', 'info');
  };

  // Short answer reveal toggle
  const toggleRevealAnswer = (idx) => {
    setRevealedAnswers((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  // Download PDF
  const handleDownloadPDF = async () => {
    if (!studyPack) return;
    try {
      setDownloadingPdf(true);
      addToast('Generating publication PDF with ReportLab...', 'info');
      const blob = await endpoints.exportPackPDF(studyPack);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cleanTitle = (studyPack.title || 'Complete_Study_Pack').replace(/[^a-zA-Z0-9_-]/g, '_');
      a.download = `${cleanTitle}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      addToast('PDF downloaded successfully!', 'success');
    } catch (err) {
      console.error('PDF export failed:', err);
      addToast(`PDF export failed: ${err.message}`, 'error');
    } finally {
      setDownloadingPdf(false);
    }
  };

  // Export CSV for Anki / Quizlet
  const handleDownloadCSV = async () => {
    if (!studyPack?.mcqs?.length) return;
    try {
      setDownloadingCsv(true);
      addToast('Generating Anki/Quizlet flashcard CSV...', 'info');
      const blob = await endpoints.exportPackCSV(studyPack);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mcqs_flashcards.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      addToast('Flashcards CSV downloaded!', 'success');
    } catch (err) {
      console.error('CSV export failed:', err);
      addToast(`CSV export failed: ${err.message}`, 'error');
    } finally {
      setDownloadingCsv(false);
    }
  };

  // Copy helpers
  const handleCopySummary = () => {
    if (!studyPack?.concise_summary) return;
    navigator.clipboard.writeText(studyPack.concise_summary);
    setCopiedSummary(true);
    addToast('Summary copied to clipboard!', 'success');
    setTimeout(() => setCopiedSummary(false), 2000);
  };

  const handleCopyJSON = () => {
    if (!studyPack) return;
    navigator.clipboard.writeText(JSON.stringify(studyPack, null, 2));
    setCopiedJson(true);
    addToast('Complete Study Pack JSON copied!', 'success');
    setTimeout(() => setCopiedJson(false), 2000);
  };

  // Filtered glossary
  const filteredGlossary = useMemo(() => {
    if (!studyPack?.glossary) return [];
    if (!glossaryQuery.trim()) return studyPack.glossary;
    const q = glossaryQuery.toLowerCase();
    return studyPack.glossary.filter(
      (item) =>
        item.term?.toLowerCase().includes(q) ||
        item.definition?.toLowerCase().includes(q)
    );
  }, [studyPack?.glossary, glossaryQuery]);

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 24px', color: '#f8fafc' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '32px', textAlign: 'center' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            borderRadius: '9999px',
            background: 'rgba(99, 102, 241, 0.15)',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            color: '#a5b4fc',
            fontSize: '0.82rem',
            fontWeight: 600,
            marginBottom: '12px',
          }}
        >
          <Sparkles size={15} /> Complete Multi-Part Study Pack Studio
        </div>
        <h1
          style={{
            fontSize: '2.4rem',
            fontWeight: 800,
            letterSpacing: '-0.02em',
            margin: '0 0 10px 0',
            background: 'linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #818cf8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          AI Study Pack Generator
        </h1>
        <p
          style={{
            maxWidth: '680px',
            margin: '0 auto',
            color: '#94a3b8',
            fontSize: '0.98rem',
            lineHeight: 1.6,
          }}
        >
          Upload a lecture PDF or paste your syllabus content. The AI synthesizes a full academic study pack:
          concise notes, 20 calibrated MCQs with explanations, 5 short-answer rubrics, a key terms glossary, and a progressive study roadmap.
        </p>
      </div>

      {/* Input Configuration Card */}
      <div
        style={{
          background: 'rgba(17, 24, 39, 0.75)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '18px',
          padding: '28px',
          marginBottom: '36px',
          boxShadow: '0 10px 30px -5px rgba(0, 0, 0, 0.4)',
        }}
      >
        {/* Input Method Tabs */}
        <div
          style={{
            display: 'flex',
            gap: '8px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            paddingBottom: '14px',
            marginBottom: '22px',
          }}
        >
          <button
            onClick={() => setInputMode('upload')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              borderRadius: '10px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9rem',
              transition: 'all 0.2s ease',
              background: inputMode === 'upload' ? 'var(--primary)' : 'rgba(255, 255, 255, 0.05)',
              color: inputMode === 'upload' ? '#ffffff' : '#94a3b8',
            }}
          >
            <Upload size={16} /> Upload Lecture PDF
          </button>

          <button
            onClick={() => setInputMode('paste')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              borderRadius: '10px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9rem',
              transition: 'all 0.2s ease',
              background: inputMode === 'paste' ? 'var(--primary)' : 'rgba(255, 255, 255, 0.05)',
              color: inputMode === 'paste' ? '#ffffff' : '#94a3b8',
            }}
          >
            <FileText size={16} /> Paste Syllabus / Notes
          </button>

          <button
            onClick={() => setInputMode('existing')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              borderRadius: '10px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9rem',
              transition: 'all 0.2s ease',
              background: inputMode === 'existing' ? 'var(--primary)' : 'rgba(255, 255, 255, 0.05)',
              color: inputMode === 'existing' ? '#ffffff' : '#94a3b8',
            }}
          >
            <BookOpen size={16} /> Choose Library Doc
          </button>
        </div>

        {/* Input Body */}
        <div style={{ marginBottom: '24px' }}>
          {inputMode === 'upload' && (
            <div>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: `2px dashed ${isDragging ? 'var(--primary)' : 'rgba(255, 255, 255, 0.15)'}`,
                  borderRadius: '14px',
                  padding: '36px 20px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  background: isDragging ? 'rgba(99, 102, 241, 0.08)' : 'rgba(15, 23, 42, 0.5)',
                  transition: 'all 0.2s ease',
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />
                <div
                  style={{
                    width: '52px',
                    height: '52px',
                    borderRadius: '12px',
                    background: 'rgba(99, 102, 241, 0.15)',
                    color: '#818cf8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 12px auto',
                  }}
                >
                  <Upload size={26} />
                </div>
                {file ? (
                  <div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc', marginBottom: '4px' }}>
                      {file.name}
                    </div>
                    <div style={{ fontSize: '0.84rem', color: '#94a3b8' }}>
                      {(file.size / 1024).toFixed(1)} KB &bull; Click or drop another file to change
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: '1rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '4px' }}>
                      Click to browse or drag & drop lecture PDF
                    </div>
                    <div style={{ fontSize: '0.82rem', color: '#64748b' }}>
                      Supports textbook chapters, lecture slide decks, syllabus outlines (.pdf up to 50MB)
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {inputMode === 'paste' && (
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                Paste syllabus text, lecture notes, or key topic outlines:
              </label>
              <textarea
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                placeholder="Example: Unit 3: Distributed Systems, Paxos Consensus, CAP Theorem, Vector Clocks, Byzantine Fault Tolerance..."
                rows={6}
                style={{
                  width: '100%',
                  borderRadius: '12px',
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#f8fafc',
                  padding: '14px',
                  fontSize: '0.92rem',
                  fontFamily: 'inherit',
                  resize: 'vertical',
                  outline: 'none',
                }}
              />
              <div style={{ fontSize: '0.75rem', color: '#64748b', textAlign: 'right', marginTop: '4px' }}>
                {pastedText.length.toLocaleString()} characters
              </div>
            </div>
          )}

          {inputMode === 'existing' && (
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                Select a document from your indexed workspace:
              </label>
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                style={{
                  width: '100%',
                  borderRadius: '12px',
                  background: '#0f172a',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#f8fafc',
                  padding: '12px 14px',
                  fontSize: '0.92rem',
                  outline: 'none',
                }}
              >
                <option value="syllabus">Default University Master Syllabus</option>
                {availableDocs.map((doc) => (
                  <option key={doc.doc_id || doc.id} value={doc.doc_id || doc.id}>
                    {doc.filename || doc.title || doc.doc_id}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Difficulty Calibration Selector */}
        <div style={{ marginBottom: '26px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
              Select Difficulty Level
            </span>
            <span style={{ fontSize: '0.8rem', color: '#818cf8' }}>
              Measurably calibrates question depth, derivations & distractors
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '12px',
            }}
          >
            {[
              {
                id: 'beginner',
                label: 'Beginner',
                color: '#34d399',
                desc: 'Foundational concepts, core definitions, intuitive explanations, straightforward MCQs.',
              },
              {
                id: 'intermediate',
                label: 'Intermediate',
                color: '#38bdf8',
                desc: 'Operational mechanics, practical implementation, standard engineering trade-offs.',
              },
              {
                id: 'advanced',
                label: 'Advanced',
                color: '#a855f7',
                desc: 'Rigorous derivations, failure modes, subtle edge cases, architectural trade-offs.',
              },
            ].map((diff) => {
              const isSelected = difficulty === diff.id;
              return (
                <div
                  key={diff.id}
                  onClick={() => setDifficulty(diff.id)}
                  style={{
                    padding: '16px',
                    borderRadius: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    border: `1.5px solid ${isSelected ? diff.color : 'rgba(255, 255, 255, 0.08)'}`,
                    background: isSelected ? 'rgba(255, 255, 255, 0.06)' : 'rgba(15, 23, 42, 0.4)',
                    boxShadow: isSelected ? `0 0 16px -2px ${diff.color}33` : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.98rem', color: isSelected ? diff.color : '#e2e8f0' }}>
                      {diff.label}
                    </span>
                    {isSelected && (
                      <span
                        style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          background: diff.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <Check size={12} color="#0f172a" strokeWidth={3} />
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.4 }}>
                    {diff.desc}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Button */}
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '10px',
              padding: '14px 36px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
              color: '#ffffff',
              fontSize: '1.02rem',
              fontWeight: 700,
              border: 'none',
              cursor: isGenerating ? 'not-allowed' : 'pointer',
              boxShadow: '0 0 24px var(--primary-glow)',
              transition: 'all 0.2s ease',
              opacity: isGenerating ? 0.75 : 1,
            }}
          >
            {isGenerating ? (
              <>
                <Loader2 size={20} className="animate-spin" /> Synthesizing Complete Study Pack...
              </>
            ) : (
              <>
                <Sparkles size={20} /> Generate Complete Study Pack
              </>
            )}
          </button>
        </div>
      </div>

      {/* Generated Study Pack Presentation */}
      {studyPack && (
        <div
          style={{
            background: 'rgba(17, 24, 39, 0.85)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '20px',
            overflow: 'hidden',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)',
          }}
        >
          {/* Pack Top Bar */}
          <div
            style={{
              padding: '24px 28px',
              background: 'rgba(15, 23, 42, 0.8)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <span
                  style={{
                    padding: '3px 10px',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    background:
                      studyPack.difficulty === 'beginner'
                        ? 'rgba(52, 211, 153, 0.2)'
                        : studyPack.difficulty === 'advanced'
                        ? 'rgba(168, 85, 247, 0.2)'
                        : 'rgba(56, 189, 248, 0.2)',
                    color:
                      studyPack.difficulty === 'beginner'
                        ? '#34d399'
                        : studyPack.difficulty === 'advanced'
                        ? '#c084fc'
                        : '#38bdf8',
                  }}
                >
                  {studyPack.difficulty} Level
                </span>
                <span style={{ fontSize: '0.82rem', color: '#64748b' }}>
                  20 MCQs &bull; 5 Short Answers &bull; {studyPack.glossary?.length || 0} Terms &bull; Roadmap
                </span>
              </div>
              <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc' }}>
                {studyPack.title || 'Complete Academic Study Pack'}
              </h2>
            </div>

            {/* Quick Exports */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              <button
                onClick={handleDownloadPDF}
                disabled={downloadingPdf}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: '10px',
                  background: 'rgba(99, 102, 241, 0.2)',
                  border: '1px solid rgba(99, 102, 241, 0.4)',
                  color: '#c7d2fe',
                  fontSize: '0.86rem',
                  fontWeight: 600,
                  cursor: downloadingPdf ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                {downloadingPdf ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
                Download PDF
              </button>

              <button
                onClick={handleDownloadCSV}
                disabled={downloadingCsv}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: '10px',
                  background: 'rgba(16, 185, 129, 0.2)',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  color: '#6ee7b7',
                  fontSize: '0.86rem',
                  fontWeight: 600,
                  cursor: downloadingCsv ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                {downloadingCsv ? <Loader2 size={15} className="animate-spin" /> : <FileSpreadsheet size={15} />}
                Export MCQs (CSV)
              </button>

              <button
                onClick={handleCopyJSON}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  borderRadius: '10px',
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#94a3b8',
                  fontSize: '0.86rem',
                  cursor: 'pointer',
                }}
              >
                {copiedJson ? <Check size={15} color="#34d399" /> : <Copy size={15} />}
                {copiedJson ? 'Copied' : 'JSON'}
              </button>
            </div>
          </div>

          {/* Sub-Navigation Tabs */}
          <div
            style={{
              display: 'flex',
              overflowX: 'auto',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              background: 'rgba(15, 23, 42, 0.5)',
              padding: '0 20px',
            }}
          >
            {[
              { id: 'roadmap', label: '1. Study Roadmap', icon: Layers, count: studyPack.suggested_study_order?.length },
              { id: 'summary', label: '2. Concise Summary', icon: BookOpen },
              { id: 'mcq', label: '3. Practice MCQs', icon: HelpCircle, count: studyPack.mcqs?.length },
              { id: 'short_answers', label: '4. Short Answers', icon: FileCheck, count: studyPack.short_answers?.length },
              { id: 'glossary', label: '5. Key Terms Glossary', icon: BookOpen, count: studyPack.glossary?.length },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activePackTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActivePackTab(tab.id)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '16px 20px',
                    border: 'none',
                    borderBottom: `2px solid ${isActive ? 'var(--primary)' : 'transparent'}`,
                    background: 'transparent',
                    color: isActive ? '#ffffff' : '#94a3b8',
                    fontWeight: isActive ? 700 : 500,
                    fontSize: '0.92rem',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <Icon size={16} color={isActive ? 'var(--primary)' : '#64748b'} />
                  {tab.label}
                  {tab.count !== undefined && (
                    <span
                      style={{
                        fontSize: '0.72rem',
                        padding: '2px 6px',
                        borderRadius: '9999px',
                        background: isActive ? 'var(--primary-glow)' : 'rgba(255, 255, 255, 0.08)',
                        color: isActive ? '#c7d2fe' : '#94a3b8',
                      }}
                    >
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Tab Content Panes */}
          <div style={{ padding: '32px 28px' }}>
            {/* 1. STUDY ROADMAP TAB */}
            {activePackTab === 'roadmap' && (
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '6px', color: '#f8fafc' }}>
                  Suggested Study Order Roadmap
                </h3>
                <p style={{ color: '#94a3b8', fontSize: '0.88rem', marginBottom: '24px' }}>
                  A calibrated chronological sequence designed to build foundational understanding before tackling complex derivations.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {(studyPack.suggested_study_order || []).map((step, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '16px',
                        padding: '18px 20px',
                        borderRadius: '14px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                      }}
                    >
                      <div
                        style={{
                          width: '34px',
                          height: '34px',
                          borderRadius: '10px',
                          background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
                          color: '#ffffff',
                          fontWeight: 700,
                          fontSize: '0.9rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        {idx + 1}
                      </div>
                      <div style={{ flex: 1, fontSize: '0.96rem', color: '#e2e8f0', lineHeight: 1.5, paddingTop: '4px' }}>
                        {step}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 2. CONCISE SUMMARY TAB */}
            {activePackTab === 'summary' && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
                    Concise Academic Summary Notes
                  </h3>
                  <button
                    onClick={handleCopySummary}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      borderRadius: '8px',
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#94a3b8',
                      fontSize: '0.82rem',
                      cursor: 'pointer',
                    }}
                  >
                    {copiedSummary ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
                    {copiedSummary ? 'Copied' : 'Copy Notes'}
                  </button>
                </div>

                <div
                  style={{
                    padding: '24px',
                    borderRadius: '14px',
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    lineHeight: 1.7,
                    fontSize: '0.95rem',
                    color: '#e2e8f0',
                  }}
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {studyPack.concise_summary || 'No summary available.'}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {/* 3. PRACTICE MCQs TAB */}
            {activePackTab === 'mcq' && (
              <div>
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '16px',
                    marginBottom: '24px',
                    paddingBottom: '16px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                  }}
                >
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
                      20 Practice Multiple Choice Questions
                    </h3>
                    <div style={{ color: '#94a3b8', fontSize: '0.86rem', marginTop: '4px' }}>
                      {quizSubmitted ? (
                        <span style={{ color: '#34d399', fontWeight: 600 }}>
                          Quiz completed! Scored {quizScore}/{(studyPack.mcqs || []).length} ({Math.round((quizScore / (studyPack.mcqs?.length || 1)) * 100)}%)
                        </span>
                      ) : (
                        `Select your answers, then submit to calculate score and reveal explanations.`
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    {!quizSubmitted ? (
                      <button
                        onClick={handleQuizSubmit}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '10px 20px',
                          borderRadius: '10px',
                          background: 'var(--primary)',
                          color: '#ffffff',
                          fontWeight: 700,
                          fontSize: '0.9rem',
                          border: 'none',
                          cursor: 'pointer',
                          boxShadow: '0 0 16px var(--primary-glow)',
                        }}
                      >
                        <CheckCircle2 size={16} /> Submit & Check Score
                      </button>
                    ) : (
                      <button
                        onClick={handleQuizReset}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '10px 18px',
                          borderRadius: '10px',
                          background: 'rgba(255, 255, 255, 0.08)',
                          color: '#f8fafc',
                          fontWeight: 600,
                          fontSize: '0.88rem',
                          border: '1px solid rgba(255, 255, 255, 0.15)',
                          cursor: 'pointer',
                        }}
                      >
                        <RotateCcw size={15} /> Retake Quiz
                      </button>
                    )}
                  </div>
                </div>

                {/* Question List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {(studyPack.mcqs || []).map((mcq, qIdx) => {
                    const userSelected = userAnswers[qIdx];
                    const correctIdx = mcq.correct_index;
                    const isCorrectAnswer =
                      userSelected !== undefined &&
                      (userSelected === correctIdx ||
                        (mcq.correct_answer && mcq.options?.[userSelected] === mcq.correct_answer));

                    return (
                      <div
                        key={qIdx}
                        style={{
                          padding: '22px',
                          borderRadius: '14px',
                          background: 'rgba(255, 255, 255, 0.03)',
                          border: `1px solid ${
                            quizSubmitted
                              ? isCorrectAnswer
                                ? 'rgba(52, 211, 153, 0.4)'
                                : 'rgba(239, 68, 68, 0.4)'
                              : 'rgba(255, 255, 255, 0.06)'
                          }`,
                        }}
                      >
                        {/* Question Prompt */}
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '16px' }}>
                          <span
                            style={{
                              padding: '4px 9px',
                              borderRadius: '6px',
                              background: 'rgba(99, 102, 241, 0.15)',
                              color: '#a5b4fc',
                              fontSize: '0.8rem',
                              fontWeight: 700,
                            }}
                          >
                            Q{qIdx + 1}
                          </span>
                          <span style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', lineHeight: 1.5 }}>
                            {mcq.question}
                          </span>
                        </div>

                        {/* Options Grid */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px', marginBottom: '14px' }}>
                          {(mcq.options || []).map((opt, optIdx) => {
                            const isChosen = userSelected === optIdx;
                            const isActualCorrect =
                              optIdx === correctIdx ||
                              (mcq.correct_answer && opt === mcq.correct_answer);

                            let optBorder = 'rgba(255, 255, 255, 0.08)';
                            let optBg = 'rgba(15, 23, 42, 0.4)';
                            let optColor = '#e2e8f0';

                            if (quizSubmitted) {
                              if (isActualCorrect) {
                                optBorder = 'rgba(52, 211, 153, 0.6)';
                                optBg = 'rgba(16, 185, 129, 0.15)';
                                optColor = '#34d399';
                              } else if (isChosen && !isActualCorrect) {
                                optBorder = 'rgba(239, 68, 68, 0.6)';
                                optBg = 'rgba(239, 68, 68, 0.15)';
                                optColor = '#f87171';
                              }
                            } else if (isChosen) {
                              optBorder = 'var(--primary)';
                              optBg = 'rgba(99, 102, 241, 0.15)';
                              optColor = '#c7d2fe';
                            }

                            const optionLetters = ['A', 'B', 'C', 'D'];

                            return (
                              <div
                                key={optIdx}
                                onClick={() => handleOptionSelect(qIdx, optIdx)}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '12px',
                                  padding: '12px 16px',
                                  borderRadius: '10px',
                                  border: `1.5px solid ${optBorder}`,
                                  background: optBg,
                                  color: optColor,
                                  cursor: quizSubmitted ? 'default' : 'pointer',
                                  fontSize: '0.9rem',
                                  transition: 'all 0.15s ease',
                                }}
                              >
                                <span
                                  style={{
                                    width: '24px',
                                    height: '24px',
                                    borderRadius: '6px',
                                    background: isChosen ? 'var(--primary)' : 'rgba(255, 255, 255, 0.08)',
                                    color: isChosen ? '#ffffff' : '#94a3b8',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 700,
                                    fontSize: '0.78rem',
                                    flexShrink: 0,
                                  }}
                                >
                                  {optionLetters[optIdx] || optIdx + 1}
                                </span>
                                <span style={{ flex: 1, lineHeight: 1.4 }}>{opt}</span>
                              </div>
                            );
                          })}
                        </div>

                        {/* Explanation reveal after submit */}
                        {quizSubmitted && mcq.explanation && (
                          <div
                            style={{
                              marginTop: '12px',
                              padding: '12px 16px',
                              borderRadius: '10px',
                              background: 'rgba(99, 102, 241, 0.08)',
                              border: '1px solid rgba(99, 102, 241, 0.2)',
                              fontSize: '0.86rem',
                              color: '#c7d2fe',
                              lineHeight: 1.5,
                            }}
                          >
                            <strong>Explanation:</strong> {mcq.explanation}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 4. SHORT ANSWERS TAB */}
            {activePackTab === 'short_answers' && (
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '6px', color: '#f8fafc' }}>
                  5 Analytical Short-Answer Questions & Grading Rubrics
                </h3>
                <p style={{ color: '#94a3b8', fontSize: '0.88rem', marginBottom: '24px' }}>
                  Practice framing precise academic answers. Toggle to inspect reference model answers and official scoring criteria.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {(studyPack.short_answers || []).map((item, idx) => {
                    const isRevealed = revealedAnswers[idx];
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '24px',
                          borderRadius: '14px',
                          background: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '14px' }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                            <span
                              style={{
                                padding: '4px 10px',
                                borderRadius: '6px',
                                background: 'rgba(139, 92, 246, 0.15)',
                                color: '#c084fc',
                                fontSize: '0.82rem',
                                fontWeight: 700,
                              }}
                            >
                              SA {idx + 1}
                            </span>
                            <span style={{ fontSize: '1.02rem', fontWeight: 600, color: '#f8fafc', lineHeight: 1.5 }}>
                              {item.question}
                            </span>
                          </div>

                          <button
                            onClick={() => toggleRevealAnswer(idx)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '6px 12px',
                              borderRadius: '8px',
                              background: isRevealed ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.06)',
                              border: '1px solid rgba(255, 255, 255, 0.1)',
                              color: isRevealed ? '#a5b4fc' : '#94a3b8',
                              fontSize: '0.82rem',
                              cursor: 'pointer',
                              flexShrink: 0,
                            }}
                          >
                            {isRevealed ? <EyeOff size={14} /> : <Eye size={14} />}
                            {isRevealed ? 'Hide Model Answer' : 'Reveal Model Answer'}
                          </button>
                        </div>

                        {/* Revealed Content */}
                        {isRevealed && (
                          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            <div
                              style={{
                                padding: '16px',
                                borderRadius: '10px',
                                background: 'rgba(15, 23, 42, 0.7)',
                                border: '1px solid rgba(56, 189, 248, 0.2)',
                              }}
                            >
                              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', marginBottom: '6px' }}>
                                Reference Model Answer
                              </div>
                              <div style={{ fontSize: '0.92rem', color: '#e2e8f0', lineHeight: 1.6 }}>
                                {item.model_answer}
                              </div>
                            </div>

                            {item.grading_criteria && item.grading_criteria.length > 0 && (
                              <div
                                style={{
                                  padding: '14px 16px',
                                  borderRadius: '10px',
                                  background: 'rgba(16, 185, 129, 0.06)',
                                  border: '1px solid rgba(16, 185, 129, 0.2)',
                                }}
                              >
                                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#34d399', textTransform: 'uppercase', marginBottom: '6px' }}>
                                  Evaluation & Grading Rubrics
                                </div>
                                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.86rem', color: '#a7f3d0', lineHeight: 1.5 }}>
                                  {item.grading_criteria.map((crit, cIdx) => (
                                    <li key={cIdx}>{crit}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 5. KEY TERMS GLOSSARY TAB */}
            {activePackTab === 'glossary' && (
              <div>
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '16px',
                    marginBottom: '24px',
                  }}
                >
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
                      Key Terms Glossary
                    </h3>
                    <div style={{ color: '#94a3b8', fontSize: '0.86rem', marginTop: '4px' }}>
                      Core technical terminology synthesized directly from the material.
                    </div>
                  </div>

                  {/* Search input */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 14px',
                      borderRadius: '10px',
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      width: '260px',
                    }}
                  >
                    <Search size={16} color="#94a3b8" />
                    <input
                      type="text"
                      value={glossaryQuery}
                      onChange={(e) => setGlossaryQuery(e.target.value)}
                      placeholder="Search terms..."
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#f8fafc',
                        fontSize: '0.88rem',
                        outline: 'none',
                        width: '100%',
                      }}
                    />
                  </div>
                </div>

                {/* Glossary Grid */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                    gap: '16px',
                  }}
                >
                  {filteredGlossary.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '18px 20px',
                        borderRadius: '12px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '1rem',
                          fontWeight: 700,
                          color: '#818cf8',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <span
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            background: 'var(--primary)',
                            display: 'inline-block',
                          }}
                        />
                        {item.term}
                      </div>
                      <div style={{ fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                        {item.definition}
                      </div>
                    </div>
                  ))}
                  {filteredGlossary.length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#64748b' }}>
                      No glossary terms matching "{glossaryQuery}"
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default StudyPackPage;
