/**
 * src/pages/StudyNotesPage.jsx
 * High-Yield Structured Study Guide Generator.
 */

import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Sparkles,
  Printer,
  Copy,
  Check,
  Zap,
  Bookmark,
  Sigma,
  FileCheck2,
  Loader2,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { DocumentSelector } from '../components/DocumentSelector';
import { AudioPlayer } from '../components/AudioPlayer';
import { useToast } from '../context/ToastContext';

export function StudyNotesPage({ initialDocId = 'syllabus' }) {
  const [selectedDocId, setSelectedDocId] = useState(initialDocId);
  const [focusTopic, setFocusTopic] = useState('');
  const [notes, setNotes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    if (initialDocId) {
      setSelectedDocId(initialDocId);
    }
  }, [initialDocId]);

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
    if (!selectedDocId) {
      addToast('Please select a knowledge source.', 'warning');
      return;
    }

    try {
      setLoading(true);
      const res = await endpoints.generateStudyNotes({
        docId: selectedDocId,
        topic: focusTopic.trim() || undefined,
      });
      setNotes(res);
      addToast('Study notes synthesized successfully!', 'success');
    } catch (err) {
      console.error('Failed to generate study notes:', err);
      addToast(`Generation failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyMarkdown = () => {
    if (!notes) return;
    let md = `# High-Yield Study Notes\n\n`;
    md += `## Executive Summary\n${notes.executive_summary}\n\n`;

    if (notes.key_concepts?.length) {
      md += `## Key Concepts\n`;
      notes.key_concepts.forEach((c) => {
        const title = c.concept || Object.keys(c)[0] || 'Concept';
        const def = c.definition || Object.values(c)[0] || '';
        md += `- **${title}**: ${def}\n`;
      });
      md += `\n`;
    }

    if (notes.formulas_and_theorems?.length) {
      md += `## Formulas & Theorems\n`;
      notes.formulas_and_theorems.forEach((f) => {
        md += `- ${f}\n`;
      });
      md += `\n`;
    }

    if (notes.high_yield_revision_points?.length) {
      md += `## High-Yield Revision Points\n`;
      notes.high_yield_revision_points.forEach((p) => {
        md += `- [ ] ${p}\n`;
      });
    }

    navigator.clipboard.writeText(md);
    setCopied(true);
    addToast('Copied notes as Markdown to clipboard!', 'success');
    setTimeout(() => setCopied(false), 2500);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ marginBottom: '8px' }}>High-Yield Study Notes Generator</h1>
        <p style={{ fontSize: '1.05rem' }}>
          Extract structured summaries, fundamental theorems, mathematical equations, and quick
          cramming checklists from your syllabus or uploaded PDFs.
        </p>
      </div>

      {/* Generation Config Card */}
      <form onSubmit={handleGenerate} className="glass-card" style={{ padding: '24px', marginBottom: '32px' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '20px',
            marginBottom: '20px',
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
              Focus Topic or Chapter (Optional):
            </label>
            <input
              type="text"
              value={focusTopic}
              onChange={(e) => setFocusTopic(e.target.value)}
              placeholder="e.g., Inverting Op-Amps, Fourier Transform, Unit 2"
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
                <span>Synthesizing Notes...</span>
              </>
            ) : (
              <>
                <Sparkles size={16} />
                <span>Generate Study Notes</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Rendered Notes View */}
      {loading && (
        <div className="glass-card" style={{ padding: '60px', textAlign: 'center' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
          <h3 style={{ marginBottom: '8px' }}>Analyzing Context & Synthesizing Formulas...</h3>
          <p style={{ color: 'var(--text-muted)' }}>
            Gemini is structuring your revision material into high-yield academic concepts.
          </p>
        </div>
      )}

      {notes && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Action Toolbar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AudioPlayer text={notes.executive_summary} />
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={handleCopyMarkdown} className="btn btn-secondary btn-sm">
                {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
              </button>
              <button onClick={handlePrint} className="btn btn-secondary btn-sm">
                <Printer size={14} />
                <span>Print / Save PDF</span>
              </button>
            </div>
          </div>

          {/* Section 1: Executive Summary */}
          <div
            className="glass-card"
            style={{
              padding: '28px',
              borderLeft: '4px solid var(--primary)',
              background:
                'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(17, 24, 39, 0.8) 100%)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '12px',
                color: 'var(--primary)',
              }}
            >
              <Zap size={20} />
              <h3 style={{ margin: 0 }}>Executive Summary</h3>
            </div>
            <p style={{ fontSize: '1.02rem', lineHeight: 1.7, color: 'var(--text-primary)' }}>
              {notes.executive_summary}
            </p>
          </div>

          {/* Section 2: Key Concepts */}
          {notes.key_concepts?.length > 0 && (
            <div className="glass-card" style={{ padding: '28px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '18px',
                  color: 'var(--secondary)',
                }}
              >
                <Bookmark size={20} />
                <h3 style={{ margin: 0 }}>Core Concepts & Definitions</h3>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '16px',
                }}
              >
                {notes.key_concepts.map((conceptObj, idx) => {
                  const title = conceptObj.concept || Object.keys(conceptObj)[0] || `Concept ${idx + 1}`;
                  const def = conceptObj.definition || Object.values(conceptObj)[0] || '';
                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '16px 20px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      <h4 style={{ color: '#a5b4fc', marginBottom: '6px' }}>{title}</h4>
                      <p style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>{def}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Section 3: Formulas & Theorems */}
          {notes.formulas_and_theorems?.length > 0 && (
            <div className="glass-card" style={{ padding: '28px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '18px',
                  color: 'var(--cyan)',
                }}
              >
                <Sigma size={20} />
                <h3 style={{ margin: 0 }}>Formulas & Theorems</h3>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {notes.formulas_and_theorems.map((formula, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '14px 18px',
                      background: 'rgba(6, 182, 212, 0.05)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid rgba(6, 182, 212, 0.2)',
                      fontFamily: 'monospace',
                      fontSize: '0.94rem',
                      color: '#67e8f9',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)' }}>#{idx + 1}</span>
                    <span>{formula}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 4: High-Yield Revision Points */}
          {notes.high_yield_revision_points?.length > 0 && (
            <div className="glass-card" style={{ padding: '28px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '18px',
                  color: 'var(--success)',
                }}
              >
                <FileCheck2 size={20} />
                <h3 style={{ margin: 0 }}>High-Yield Exam Revision Points</h3>
              </div>

              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {notes.high_yield_revision_points.map((point, idx) => (
                  <li
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px',
                      fontSize: '0.94rem',
                      lineHeight: 1.6,
                    }}
                  >
                    <span
                      style={{
                        minWidth: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        background: 'rgba(16, 185, 129, 0.2)',
                        color: 'var(--success)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        marginTop: '2px',
                      }}
                    >
                      ✓
                    </span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
