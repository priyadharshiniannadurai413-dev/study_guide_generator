import React, { useState } from 'react';
import {
  Globe,
  Loader2,
  ArrowRight,
  FileText,
  AlertCircle,
  Sparkles,
  Shield,
  BookOpen,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { endpoints } from '../../api/endpoints';

export const FetchConnectorCard: React.FC = () => {
  const { getToken } = useAuth();
  const [testUrl, setTestUrl] = useState('https://en.wikipedia.org/wiki/Static_random-access_memory');
  const [question, setQuestion] = useState('What is SRAM? Explain its working, advantages and disadvantages.');
  const [mode, setMode] = useState<'ask' | 'notes'>('ask');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Result state
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [studyNotes, setStudyNotes] = useState<any | null>(null);
  const [sourceMeta, setSourceMeta] = useState<{ url: string; title: string; word_count?: number } | null>(null);

  // Debug raw markdown
  const [rawMarkdown, setRawMarkdown] = useState<string | null>(null);
  const [showRawMarkdown, setShowRawMarkdown] = useState(false);

  // Auto-enrichment preference persisted in localStorage
  const [autoEnrich, setAutoEnrich] = useState<boolean>(() => {
    return localStorage.getItem('studysync_mcp_fetch_auto_enrich') === 'true';
  });

  const [sessionFetches, setSessionFetches] = useState<number>(() => {
    const saved = sessionStorage.getItem('studysync_mcp_fetch_count');
    return saved ? parseInt(saved, 10) : 0;
  });

  const toggleAutoEnrich = () => {
    const next = !autoEnrich;
    setAutoEnrich(next);
    localStorage.setItem('studysync_mcp_fetch_auto_enrich', String(next));
  };

  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUrl = testUrl.trim();
    if (!cleanUrl) return;

    try {
      setLoading(true);
      setErrorMsg(null);
      setAiAnswer(null);
      setStudyNotes(null);
      setSourceMeta(null);
      setRawMarkdown(null);

      if (mode === 'ask') {
        const q = question.trim() || 'Explain the primary concepts and summary of this webpage.';
        const res = await endpoints.askWebQuestion({ url: cleanUrl, question: q });
        if (res?.success) {
          setAiAnswer(res.answer);
          setSourceMeta(res.source || { url: cleanUrl, title: 'Web Source' });
        } else {
          setErrorMsg(res?.detail || 'Failed to generate an answer from the webpage.');
        }
      } else {
        const topic = question.trim() || undefined;
        const res = await endpoints.generateWebStudyNotes({ url: cleanUrl, topic, difficulty: 'intermediate' });
        if (res?.success) {
          setStudyNotes(res.notes);
          setSourceMeta(res.source || { url: cleanUrl, title: 'Web Source' });
        } else {
          setErrorMsg(res?.detail || 'Failed to synthesize study notes from the webpage.');
        }
      }

      const newCount = sessionFetches + 1;
      setSessionFetches(newCount);
      sessionStorage.setItem('studysync_mcp_fetch_count', String(newCount));
    } catch (err: any) {
      console.error('[FetchConnectorCard] Execution error:', err);
      setErrorMsg(err?.message || 'Error occurred while retrieving or processing the webpage.');
    } finally {
      setLoading(false);
    }
  };

  const handleFetchRawPreview = async () => {
    if (rawMarkdown) {
      setShowRawMarkdown(!showRawMarkdown);
      return;
    }
    const cleanUrl = testUrl.trim();
    if (!cleanUrl) return;
    try {
      setLoading(true);
      const res = await endpoints.fetchWebDocument(cleanUrl);
      if (res?.success) {
        setRawMarkdown(res.content);
        setShowRawMarkdown(true);
      }
    } catch (err: any) {
      console.error('[FetchConnectorCard] Raw fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        background: 'rgba(15, 23, 42, 0.85)',
        border: '1px solid rgba(51, 65, 85, 0.6)',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.4)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        backdropFilter: 'blur(16px)',
      }}
    >
      <div>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: '16px',
            borderBottom: '1px solid rgba(51, 65, 85, 0.6)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                padding: '10px',
                background: 'rgba(37, 99, 235, 0.15)',
                borderRadius: '12px',
                color: '#60a5fa',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(59, 130, 246, 0.3)',
              }}
            >
              <Globe size={22} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                Fetch MCP Connector
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                Fetch MCP Web Extraction & Grounded AI Synthesis
              </p>
            </div>
          </div>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '999px',
              fontSize: '0.75rem',
              fontWeight: 600,
              background: 'rgba(6, 78, 59, 0.5)',
              color: '#34d399',
              border: '1px solid rgba(16, 185, 129, 0.3)',
            }}
          >
            <CheckCircle2 size={12} />
            Ready
          </span>
        </div>

        {/* Global Auto-Enrichment Toggle */}
        <div
          style={{
            marginTop: '16px',
            marginBottom: '16px',
            padding: '12px 14px',
            background: 'rgba(30, 41, 59, 0.5)',
            borderRadius: '12px',
            border: '1px solid rgba(51, 65, 85, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="#60a5fa" />
            <div>
              <div style={{ fontSize: '0.80rem', fontWeight: 600, color: '#f8fafc' }}>
                Auto-Enrich Study Guides
              </div>
              <div style={{ fontSize: '0.70rem', color: '#94a3b8' }}>
                Fetch external web documentation when course materials need enrichment
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={toggleAutoEnrich}
            style={{
              width: '42px',
              height: '22px',
              borderRadius: '999px',
              background: autoEnrich ? '#2563eb' : '#334155',
              position: 'relative',
              border: 'none',
              cursor: 'pointer',
              transition: 'background 0.2s ease',
            }}
          >
            <span
              style={{
                position: 'absolute',
                top: '2px',
                left: autoEnrich ? '22px' : '2px',
                width: '18px',
                height: '18px',
                borderRadius: '50%',
                background: '#ffffff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
                transition: 'left 0.2s ease',
              }}
            />
          </button>
        </div>

        {/* Academic Source Filter Badges */}
        <div style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', fontSize: '0.74rem', color: '#94a3b8' }}>
            <Shield size={13} color="#34d399" />
            <span>Supported Academic & Technical Sources:</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {['.edu / .gov', 'docs.python.org', 'fastapi.tiangolo.com', 'react.dev', 'Wikipedia', 'ArXiv', 'IETF'].map((tag) => (
              <span
                key={tag}
                style={{
                  fontSize: '0.68rem',
                  padding: '2px 8px',
                  borderRadius: '6px',
                  background: 'rgba(30, 41, 59, 0.7)',
                  border: '1px solid rgba(51, 65, 85, 0.7)',
                  color: '#cbd5e1',
                  fontFamily: 'monospace',
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Mode Selector */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '14px' }}>
          <button
            type="button"
            onClick={() => setMode('ask')}
            style={{
              padding: '8px 10px',
              borderRadius: '8px',
              border: mode === 'ask' ? '1.5px solid #3b82f6' : '1px solid rgba(51, 65, 85, 0.8)',
              background: mode === 'ask' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(15, 23, 42, 0.6)',
              color: mode === 'ask' ? '#93c5fd' : '#94a3b8',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <Sparkles size={14} />
            Ask Web Question
          </button>
          <button
            type="button"
            onClick={() => setMode('notes')}
            style={{
              padding: '8px 10px',
              borderRadius: '8px',
              border: mode === 'notes' ? '1.5px solid #8b5cf6' : '1px solid rgba(51, 65, 85, 0.8)',
              background: mode === 'notes' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(15, 23, 42, 0.6)',
              color: mode === 'notes' ? '#c4b5fd' : '#94a3b8',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <BookOpen size={14} />
            Synthesize Study Notes
          </button>
        </div>

        {/* Live URL + Question Form */}
        <form onSubmit={handleExecute} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '6px' }}>
              Target Web Documentation URL:
            </label>
            <input
              type="url"
              value={testUrl}
              onChange={(e) => setTestUrl(e.target.value)}
              placeholder="https://en.wikipedia.org/wiki/..."
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'rgba(2, 6, 23, 0.8)',
                border: '1px solid rgba(51, 65, 85, 0.8)',
                borderRadius: '8px',
                fontSize: '0.8rem',
                color: '#f8fafc',
                boxSizing: 'border-box',
                outline: 'none',
              }}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '6px' }}>
              {mode === 'ask' ? 'Student Inquiry / Question:' : 'Focus Topic or Chapter (Optional):'}
            </label>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={mode === 'ask' ? 'e.g., What is SRAM? Explain its working, advantages and disadvantages.' : 'e.g., SRAM cell architecture and operational cycle'}
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'rgba(2, 6, 23, 0.8)',
                border: '1px solid rgba(51, 65, 85, 0.8)',
                borderRadius: '8px',
                fontSize: '0.8rem',
                color: '#f8fafc',
                boxSizing: 'border-box',
                outline: 'none',
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !testUrl.trim()}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '10px 16px',
              background: mode === 'ask' ? '#2563eb' : '#7c3aed',
              color: '#ffffff',
              fontSize: '0.82rem',
              fontWeight: 600,
              borderRadius: '8px',
              border: 'none',
              cursor: loading || !testUrl.trim() ? 'not-allowed' : 'pointer',
              opacity: loading || !testUrl.trim() ? 0.6 : 1,
              transition: 'background 0.2s ease',
            }}
          >
            {loading ? (
              <>
                <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                <span>{mode === 'ask' ? 'Fetching & Synthesizing AI Answer...' : 'Synthesizing Full Study Notes...'}</span>
              </>
            ) : (
              <>
                <ArrowRight size={16} />
                <span>{mode === 'ask' ? 'Ask AI from Web' : 'Generate Study Notes from Web'}</span>
              </>
            )}
          </button>
        </form>

        {/* Error Alert */}
        {errorMsg && (
          <div
            style={{
              marginTop: '14px',
              padding: '12px 14px',
              background: 'rgba(127, 29, 29, 0.3)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              borderRadius: '10px',
              fontSize: '0.78rem',
              color: '#fca5a5',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Primary AI Result: Answer Display */}
        {aiAnswer && (
          <div
            style={{
              marginTop: '16px',
              padding: '16px',
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(59, 130, 246, 0.4)',
              borderRadius: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#60a5fa', fontWeight: 700, fontSize: '0.84rem' }}>
                <Sparkles size={16} />
                <span>AI Grounded Answer</span>
              </div>
              {sourceMeta && (
                <a
                  href={sourceMeta.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '0.72rem',
                    color: '#94a3b8',
                    textDecoration: 'none',
                  }}
                >
                  <ExternalLink size={12} />
                  <span>{sourceMeta.title || 'Source'}</span>
                </a>
              )}
            </div>

            <div
              style={{
                fontSize: '0.82rem',
                color: '#f1f5f9',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
              }}
            >
              {aiAnswer}
            </div>

            {sourceMeta && (
              <div
                style={{
                  paddingTop: '10px',
                  borderTop: '1px solid rgba(51, 65, 85, 0.6)',
                  fontSize: '0.72rem',
                  color: '#94a3b8',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <Globe size={13} color="#60a5fa" />
                <span>
                  Source: <strong>{sourceMeta.title}</strong> — {sourceMeta.url}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Primary AI Result: Study Notes Display */}
        {studyNotes && (
          <div
            style={{
              marginTop: '16px',
              padding: '16px',
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(139, 92, 246, 0.4)',
              borderRadius: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#c084fc', fontWeight: 700, fontSize: '0.86rem' }}>
                <BookOpen size={16} />
                <span>{studyNotes.title || studyNotes.topic_title || 'Synthesized Study Notes'}</span>
              </div>
              {sourceMeta && (
                <a
                  href={sourceMeta.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '0.72rem',
                    color: '#94a3b8',
                    textDecoration: 'none',
                  }}
                >
                  <ExternalLink size={12} />
                  <span>{sourceMeta.title}</span>
                </a>
              )}
            </div>

            {studyNotes.executive_summary && (
              <p style={{ margin: 0, fontSize: '0.80rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                {studyNotes.executive_summary}
              </p>
            )}

            {/* Sections */}
            {studyNotes.sections?.slice(0, 3).map((sec: any, idx: number) => (
              <div
                key={idx}
                style={{
                  padding: '10px 12px',
                  background: 'rgba(15, 23, 42, 0.6)',
                  borderRadius: '8px',
                  border: '1px solid rgba(51, 65, 85, 0.5)',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '0.80rem', color: '#f8fafc', marginBottom: '4px' }}>
                  {sec.title}
                </div>
                <div style={{ fontSize: '0.76rem', color: '#94a3b8', lineHeight: 1.4 }}>
                  {sec.overview}
                </div>
                {sec.key_points?.length > 0 && (
                  <ul style={{ margin: '6px 0 0 16px', padding: 0, fontSize: '0.74rem', color: '#cbd5e1' }}>
                    {sec.key_points.slice(0, 3).map((kp: string, kidx: number) => (
                      <li key={kidx}>{kp}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Collapsible Raw Source Preview for Debugging */}
        <div style={{ marginTop: '14px' }}>
          <button
            type="button"
            onClick={handleFetchRawPreview}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              fontSize: '0.72rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: 0,
            }}
          >
            {showRawMarkdown ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            <span>View Extracted Source Markdown (Debugging / Verification)</span>
          </button>

          {showRawMarkdown && rawMarkdown && (
            <div
              style={{
                marginTop: '8px',
                padding: '10px 12px',
                background: 'rgba(2, 6, 23, 0.95)',
                border: '1px solid rgba(51, 65, 85, 0.8)',
                borderRadius: '8px',
                maxHeight: '160px',
                overflowY: 'auto',
                fontSize: '0.70rem',
                fontFamily: 'monospace',
                color: '#94a3b8',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {rawMarkdown.substring(0, 800)}...
            </div>
          )}
        </div>
      </div>

      <div
        style={{
          paddingTop: '16px',
          marginTop: '20px',
          borderTop: '1px solid rgba(51, 65, 85, 0.6)',
          fontSize: '0.72rem',
          color: '#64748b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>
          Transport: <strong style={{ color: '#94a3b8' }}>Fetch MCP (Clean Extractor)</strong>
        </span>
        <span>
          Auto-Enrich: <strong style={{ color: autoEnrich ? '#34d399' : '#94a3b8' }}>{autoEnrich ? 'ACTIVE' : 'OFF'}</strong>
        </span>
      </div>
    </div>
  );
};
