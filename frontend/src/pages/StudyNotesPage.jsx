/**
 * src/pages/StudyNotesPage.jsx
 * High-Yield Structured Study Guide Generator.
 */

import React, { useState, useEffect, useRef } from 'react';
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
  FileDown,
  Loader2,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { DocumentSelector } from '../components/DocumentSelector';
import { AudioPlayer } from '../components/AudioPlayer';
import { StudyDocumentViewer } from '../components/study/StudyDocumentViewer';
import { useToast } from '../context/ToastContext';

export function StudyNotesPage({ initialDocId = 'syllabus' }) {
  const [selectedDocId, setSelectedDocId] = useState(initialDocId);
  const [webUrl, setWebUrl] = useState('');
  const [focusTopic, setFocusTopic] = useState('');
  const [difficulty, setDifficulty] = useState('intermediate');
  const [enableWeb, setEnableWeb] = useState(() => {
    return localStorage.getItem('studysync_mcp_fetch_auto_enrich') === 'true';
  });
  const [notes, setNotes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [genProgress, setGenProgress] = useState(0);
  const [genStatusText, setGenStatusText] = useState('');
  const genIntervalRef = useRef(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingDocx, setDownloadingDocx] = useState(false);
  const [copied, setCopied] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    if (initialDocId) {
      setSelectedDocId(initialDocId);
    }
  }, [initialDocId]);

  useEffect(() => {
    return () => {
      if (genIntervalRef.current) clearInterval(genIntervalRef.current);
    };
  }, []);

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
    if (!selectedDocId && !webUrl.trim()) {
      addToast('Please select a knowledge source or provide a web URL.', 'warning');
      return;
    }

    try {
      setLoading(true);
      setGenProgress(15);
      setGenStatusText(
        webUrl.trim()
          ? 'Fetching & extracting webpage content via Fetch MCP...'
          : 'Retrieving vector context & course syllabus...'
      );

      let current = 15;
      if (genIntervalRef.current) clearInterval(genIntervalRef.current);
      genIntervalRef.current = setInterval(() => {
        current += Math.floor(Math.random() * 8) + 4;
        if (current > 92) current = 92;
        setGenProgress(current);

        if (current >= 35 && current < 65) {
          setGenStatusText(
            webUrl.trim()
              ? 'Cleaning HTML boilerplate & isolating core article sections...'
              : 'Synthesizing technical definitions & core concepts...'
          );
        } else if (current >= 65 && current < 88) {
          setGenStatusText('Drafting syntax rules, formulas, and architecture diagrams...');
        } else if (current >= 88) {
          setGenStatusText('Formulating actionable takeaways & revision checklists...');
        }
      }, 350);

      const res = await endpoints.generateStudyNotes({
        docId: webUrl.trim() ? undefined : selectedDocId,
        url: webUrl.trim() || undefined,
        topic: focusTopic.trim() || undefined,
        difficulty,
        enableWeb: Boolean(enableWeb || webUrl.trim()),
      });

      if (genIntervalRef.current) clearInterval(genIntervalRef.current);
      setGenProgress(100);
      setGenStatusText('Notes synthesized successfully!');
      await new Promise((r) => setTimeout(r, 450));

      setNotes(res);
      addToast('Study notes synthesized successfully!', 'success');
    } catch (err) {
      if (genIntervalRef.current) clearInterval(genIntervalRef.current);
      console.error('Failed to generate study notes:', err);
      addToast(`Generation failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyMarkdown = () => {
    if (!notes) return;
    const title = notes.title || notes.topic_title || 'High-Yield Study Notes';
    let md = `# ${title}\n\n`;
    if (notes.executive_summary) {
      md += `## Executive Summary\n${notes.executive_summary}\n\n`;
    }

    if (notes.sections?.length) {
      md += `## Detailed Breakdown & Architecture\n\n`;
      notes.sections.forEach((sec) => {
        md += `### ${sec.title}\n${sec.overview}\n\n`;
        if (sec.key_points?.length) {
          sec.key_points.forEach((kp) => {
            md += `- ${kp}\n`;
          });
          md += `\n`;
        }
        if (sec.code_or_syntax) {
          md += `\`\`\`\n${sec.code_or_syntax}\n\`\`\`\n\n`;
        }
      });
    } else {
      const concepts = notes.core_concepts?.length ? notes.core_concepts : (notes.key_concepts || []);
      if (concepts.length) {
        md += `## Core Concepts & Definitions\n`;
        concepts.forEach((c) => {
          const cTitle = c.term || c.concept || Object.keys(c)[0] || 'Concept';
          const def = c.definition || Object.values(c)[0] || '';
          md += `- **${cTitle}**: ${def}\n`;
          if (c.syntax_or_example) {
            md += `  \`\`\`\n  ${c.syntax_or_example}\n  \`\`\`\n`;
          }
        });
        md += `\n`;
      }
    }

    const formulas = notes.syntax_and_formulas?.length ? notes.syntax_and_formulas : (notes.formulas_and_theorems || []);
    if (formulas.length && !notes.sections?.length) {
      md += `## Syntax Rules & Formulas\n`;
      formulas.forEach((f) => {
        md += `- ${f}\n`;
      });
      md += `\n`;
    }

    const takeaways = notes.actionable_takeaways?.length ? notes.actionable_takeaways : (notes.high_yield_revision_points || []);
    if (takeaways.length) {
      md += `## Actionable Takeaways & Implementation Checkpoints\n`;
      takeaways.forEach((p) => {
        md += `- [ ] ${p}\n`;
      });
    }

    navigator.clipboard.writeText(md);
    setCopied(true);
    addToast('Copied notes as Markdown to clipboard!', 'success');
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownloadPDF = async () => {
    if (!notes) return;
    try {
      setDownloadingPdf(true);
      addToast('Preparing formatted PDF...', 'info');
      const blob = await endpoints.exportPDF({
        notes,
        topic: notes.title || notes.topic_title || focusTopic,
        docId: selectedDocId,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cleanTitle = (notes.title || notes.topic_title || 'study_notes').replace(/[^a-zA-Z0-9_-]/g, '_');
      a.download = `${cleanTitle}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      addToast('PDF downloaded successfully!', 'success');
    } catch (err) {
      console.error('Failed to download PDF:', err);
      addToast(`PDF download failed: ${err.message}`, 'error');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadDOCX = async () => {
    if (!notes) return;
    try {
      setDownloadingDocx(true);
      addToast('Preparing formatted Word document...', 'info');
      const blob = await endpoints.exportDOCX({
        notes,
        topic: notes.title || notes.topic_title || focusTopic,
        docId: selectedDocId,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cleanTitle = (notes.title || notes.topic_title || 'study_notes').replace(/[^a-zA-Z0-9_-]/g, '_');
      a.download = `${cleanTitle}.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      addToast('Word document downloaded successfully!', 'success');
    } catch (err) {
      console.error('Failed to download Word doc:', err);
      addToast(`Word download failed: ${err.message}`, 'error');
    } finally {
      setDownloadingDocx(false);
    }
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
              Or Web Documentation URL (Fetch MCP Web Extraction):
            </label>
            <input
              type="url"
              value={webUrl}
              onChange={(e) => setWebUrl(e.target.value)}
              placeholder="e.g., https://en.wikipedia.org/wiki/Static_random-access_memory or https://docs.python.org/3/..."
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
              Academic Depth / Difficulty Level:
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
                  badge: 'Introductory',
                  desc: 'Foundational concepts, intuitive analogies, core definitions',
                },
                {
                  id: 'intermediate',
                  label: 'Intermediate',
                  badge: 'Standard Degree',
                  desc: 'Operational mechanics, practical workflows, standard trade-offs',
                },
                {
                  id: 'advanced',
                  label: 'Advanced',
                  badge: 'Rigorous / Systems',
                  desc: 'Deep theoretical rigor, edge cases, failure modes, optimizations',
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
                Synthesizing Study Notes
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
              {genStatusText || 'Structuring conceptual breakdown...'}
            </span>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} Tier
            </span>
          </div>
        </div>
      )}

      {notes && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Secondary Utility Controls */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
              padding: '0 4px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AudioPlayer text={notes.executive_summary || notes.quick_summary} />
            </div>

            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button
                onClick={handleDownloadDOCX}
                disabled={downloadingDocx}
                className="btn btn-secondary btn-sm"
                title="Download formatted Microsoft Word document (.docx)"
              >
                {downloadingDocx ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <FileDown size={14} />}
                <span>{downloadingDocx ? 'Exporting Word...' : 'Download Word (.docx)'}</span>
              </button>
              <button onClick={handleCopyMarkdown} className="btn btn-secondary btn-sm">
                {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
              </button>
              <button onClick={handlePrint} className="btn btn-secondary btn-sm">
                <Printer size={14} />
                <span>Print</span>
              </button>
            </div>
          </div>

          {/* Unified Continuous Document Reader */}
          <StudyDocumentViewer
            notes={notes}
            topic={notes.title || notes.topic_title || focusTopic || 'Study Guide'}
            docId={selectedDocId}
          />
        </div>
      )}
    </div>
  );
}
