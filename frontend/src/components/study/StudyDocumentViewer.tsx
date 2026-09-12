import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Download, FileText, Loader2, BookOpen, Globe, ExternalLink } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { getEffectiveToken, API_BASE } from '../../api/client';

export interface StudySection {
  title: string;
  overview: string;
  key_points: string[];
  code_or_syntax?: string | null;
}

export interface StudyNotesData {
  title?: string;
  topic_title?: string;
  executive_summary?: string;
  quick_summary?: string;
  sections?: StudySection[];
  core_concepts?: Array<{
    term?: string;
    concept?: string;
    definition?: string;
    syntax_or_example?: string | null;
  }>;
  actionable_takeaways?: string[];
  high_yield_revision_points?: string[];
  sources?: {
    rag?: string[];
    web?: Array<{
      title?: string;
      url?: string;
      tier?: string;
    }>;
  };
}

interface Props {
  notes: StudyNotesData;
  topic: string;
  docId?: string;
}

export const StudyDocumentViewer: React.FC<Props> = ({ notes, topic, docId }) => {
  const { getToken } = useAuth();
  const [downloading, setDownloading] = useState(false);

  // Normalize sections from adaptive schema or legacy concepts
  const normalizedSections: StudySection[] = React.useMemo(() => {
    if (notes.sections && notes.sections.length > 0) {
      return notes.sections;
    }
    if (notes.core_concepts && notes.core_concepts.length > 0) {
      return notes.core_concepts.map((c) => ({
        title: c.term || c.concept || 'Key Concept',
        overview: c.definition || '',
        key_points: [],
        code_or_syntax: c.syntax_or_example || null,
      }));
    }
    return [];
  }, [notes]);

  const displayTitle = notes.title || notes.topic_title || topic || 'Study Guide';
  const displaySummary = notes.executive_summary || notes.quick_summary || '';
  const takeaways = notes.actionable_takeaways?.length
    ? notes.actionable_takeaways
    : notes.high_yield_revision_points || [];

  const handleDownloadPdf = async () => {
    try {
      setDownloading(true);
      let token: string | null = null;
      try {
        if (getToken) {
          token = await getToken();
        }
      } catch (err) {
        console.warn('Could not get token from useAuth:', err);
      }
      if (!token) {
        token = await getEffectiveToken();
      }

      const params = new URLSearchParams({
        topic: displayTitle,
        file_format: 'pdf',
        ...(docId ? { doc_id: docId } : {}),
      });

      const endpointUrl = `${API_BASE}/api/study/export-notes?${params.toString()}`;

      const res = await fetch(endpointUrl, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        throw new Error(`Failed to download PDF (HTTP ${res.status})`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${displayTitle.toLowerCase().replace(/[^a-z0-9]+/g, '_')}_study_guide.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Download error:', err);
      alert(`Error downloading PDF study guide: ${err.message || err}`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto my-8">
      {/* Sticky Action Toolbar */}
      <div
        className="sticky top-4 z-20 flex items-center justify-between p-4 mb-6 bg-slate-900/90 backdrop-blur border border-slate-700 rounded-xl shadow-lg"
        style={{
          backgroundColor: 'rgba(15, 23, 42, 0.92)',
          backdropFilter: 'blur(8px)',
          borderColor: 'rgba(51, 65, 85, 1)',
        }}
      >
        <div className="flex items-center space-x-2 text-white font-medium" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff' }}>
          <FileText className="w-5 h-5 text-indigo-400" size={20} color="#818cf8" />
          <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{displayTitle}</span>
        </div>
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          className="flex items-center px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 active:scale-95 transition rounded-lg shadow disabled:opacity-50"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            borderRadius: '8px',
            backgroundColor: '#4f46e5',
            color: '#ffffff',
            border: 'none',
            cursor: downloading ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: '0.88rem',
            opacity: downloading ? 0.6 : 1,
            transition: 'all 0.2s ease',
          }}
        >
          {downloading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" size={16} style={{ animation: 'spin 1s linear infinite' }} />
              <span>Generating PDF...</span>
            </>
          ) : (
            <>
              <Download className="w-4 h-4 mr-2" size={16} />
              <span>Download PDF</span>
            </>
          )}
        </button>
      </div>

      {/* Unified Document Reader (Print-Ready / Textbook Style) */}
      <div
        className="bg-white text-slate-900 p-10 md:p-14 rounded-2xl shadow-xl border border-slate-200 leading-relaxed font-sans"
        style={{
          backgroundColor: '#ffffff',
          color: '#0f172a',
          padding: '40px 48px',
          borderRadius: '16px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          border: '1px solid #e2e8f0',
          fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
          lineHeight: 1.7,
        }}
      >
        {/* Document Header */}
        <div
          className="border-b border-slate-200 pb-6 mb-8"
          style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '24px', marginBottom: '32px' }}
        >
          <span
            className="text-xs uppercase font-bold tracking-widest text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full"
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: '#4f46e5',
              backgroundColor: '#eef2ff',
              padding: '4px 12px',
              borderRadius: '9999px',
              display: 'inline-block',
            }}
          >
            Comprehensive Study Guide
          </span>
          <h1
            className="text-3xl font-extrabold text-slate-900 mt-4 tracking-tight"
            style={{
              fontSize: '1.95rem',
              fontWeight: 800,
              color: '#0f172a',
              marginTop: '16px',
              marginBottom: '0',
              letterSpacing: '-0.025em',
            }}
          >
            {displayTitle}
          </h1>
        </div>

        {/* Executive Summary */}
        {displaySummary && (
          <div className="mb-10" style={{ marginBottom: '36px' }}>
            <h2
              className="text-xl font-bold text-slate-900 mb-3 border-l-4 border-indigo-600 pl-3"
              style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                color: '#0f172a',
                borderLeft: '4px solid #4f46e5',
                paddingLeft: '12px',
                marginBottom: '12px',
              }}
            >
              Executive Summary
            </h2>
            <p
              className="text-slate-700 whitespace-pre-line text-base leading-7"
              style={{
                color: '#334155',
                whiteSpace: 'pre-line',
                fontSize: '1rem',
                lineHeight: 1.75,
                margin: 0,
              }}
            >
              {displaySummary}
            </p>
          </div>
        )}

        {/* Core Sections (Sequential Continuous Flow) */}
        <div className="space-y-10" style={{ display: 'flex', flexDirection: 'column', gap: '36px' }}>
          {normalizedSections.map((section, idx) => (
            <div
              key={idx}
              className="border-t border-slate-100 pt-6"
              style={{ borderTop: '1px solid #f1f5f9', paddingTop: '24px' }}
            >
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{
                  fontSize: '1.15rem',
                  fontWeight: 700,
                  color: '#0f172a',
                  marginBottom: '8px',
                }}
              >
                {idx + 1}. {section.title}
              </h3>
              {section.overview && (
                <p
                  className="text-slate-700 text-sm md:text-base mb-4 leading-6"
                  style={{
                    color: '#334155',
                    fontSize: '0.96rem',
                    lineHeight: 1.65,
                    marginBottom: '16px',
                  }}
                >
                  {section.overview}
                </p>
              )}

              {/* Key Bulleted Points */}
              {section.key_points && section.key_points.length > 0 && (
                <ul
                  className="list-disc pl-5 space-y-1.5 text-sm md:text-base text-slate-700 mb-4"
                  style={{
                    listStyleType: 'disc',
                    paddingLeft: '20px',
                    color: '#334155',
                    fontSize: '0.94rem',
                    lineHeight: 1.6,
                    marginBottom: '16px',
                  }}
                >
                  {section.key_points.map((pt, pIdx) => (
                    <li key={pIdx} style={{ marginBottom: '6px' }}>
                      {pt}
                    </li>
                  ))}
                </ul>
              )}

              {/* Code or Formula Block (Only rendered if present) */}
              {section.code_or_syntax && (
                <div
                  className="my-3 p-4 bg-slate-900 text-slate-100 rounded-lg overflow-x-auto text-xs md:text-sm font-mono"
                  style={{
                    margin: '12px 0',
                    padding: '16px',
                    backgroundColor: '#0f172a',
                    color: '#f8fafc',
                    borderRadius: '8px',
                    overflowX: 'auto',
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    fontSize: '0.86rem',
                    lineHeight: 1.5,
                  }}
                >
                  <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                    {section.code_or_syntax}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Actionable Takeaways */}
        {takeaways && takeaways.length > 0 && (
          <div
            className="mt-12 pt-8 border-t-2 border-slate-200 bg-slate-50 p-6 rounded-xl"
            style={{
              marginTop: '44px',
              paddingTop: '28px',
              borderTop: '2px solid #e2e8f0',
              backgroundColor: '#f8fafc',
              padding: '24px',
              borderRadius: '12px',
            }}
          >
            <h2
              className="text-lg font-bold text-slate-900 mb-3"
              style={{
                fontSize: '1.15rem',
                fontWeight: 700,
                color: '#0f172a',
                marginBottom: '12px',
              }}
            >
              Actionable Implementation Takeaways
            </h2>
            <ul
              className="list-disc pl-5 space-y-2 text-sm text-slate-700"
              style={{
                listStyleType: 'disc',
                paddingLeft: '20px',
                color: '#334155',
                fontSize: '0.92rem',
                lineHeight: 1.6,
                margin: 0,
              }}
            >
              {takeaways.map((item, idx) => (
                <li key={idx} style={{ marginBottom: '8px' }}>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Verified External Citations (Fetch MCP) */}
        {notes.sources?.web && notes.sources.web.length > 0 && (
          <div
            style={{
              marginTop: '32px',
              padding: '20px 24px',
              border: '1px solid #cbd5e1',
              backgroundColor: '#f1f5f9',
              borderRadius: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Globe size={18} color="#2563eb" />
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#0f172a' }}>
                Verified External Web Citations (Fetch MCP)
              </h3>
            </div>
            <p style={{ margin: '0 0 14px', fontSize: '0.82rem', color: '#64748b' }}>
              These external technical references were dynamically retrieved and validated to enrich this study guide:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {notes.sources.web.map((src, i) => (
                <a
                  key={i}
                  href={src.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    backgroundColor: '#ffffff',
                    border: '1px solid #e2e8f0',
                    textDecoration: 'none',
                    color: '#1e293b',
                    fontSize: '0.84rem',
                    fontWeight: 500,
                    transition: 'border-color 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <span style={{ fontSize: '0.70rem', background: '#dbeafe', color: '#1e40af', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                      {src.tier || 'DOCS'}
                    </span>
                    <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {src.title || src.url}
                    </span>
                  </div>
                  <ExternalLink size={14} color="#64748b" style={{ flexShrink: 0, marginLeft: '8px' }} />
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StudyDocumentViewer;
