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
  const [focusTopic, setFocusTopic] = useState('');
  const [notes, setNotes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingDocx, setDownloadingDocx] = useState(false);
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
