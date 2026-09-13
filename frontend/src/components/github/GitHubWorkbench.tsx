import React, { useState } from 'react';
import { FolderGit2, Search, Code, FileText, Loader2, RefreshCw, AlertCircle } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getEffectiveToken, API_BASE } from '../../api/client';

export const GitHubWorkbench: React.FC = () => {
  const { getToken } = useAuth();
  const [repoQuery, setRepoQuery] = useState('');
  const [filePath, setFilePath] = useState('');
  const [action, setAction] = useState<'search' | 'read' | 'review'>('search');
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const getAuthToken = async (): Promise<string> => {
    try {
      const clerkToken = await getToken();
      if (clerkToken) return clerkToken;
    } catch {
      // Fallback
    }
    return await getEffectiveToken();
  };

  const executeOperation = async () => {
    if (!repoQuery.trim()) return;
    try {
      setLoading(true);
      setResult(null);
      setErrorMsg(null);
      const token = await getAuthToken();

      let queryPrompt = '';
      if (action === 'search') {
        queryPrompt = `Use github tools to search repositories for: ${repoQuery.trim()}`;
      } else if (action === 'read') {
        const pathStr = filePath.trim() ? filePath.trim() : 'README.md';
        queryPrompt = `Fetch and display the file contents of '${pathStr}' in repository '${repoQuery.trim()}' using github tools.`;
      } else {
        const pathStr = filePath.trim() ? filePath.trim() : 'main source code';
        queryPrompt = `Perform a comprehensive academic code review on '${pathStr}' in repository '${repoQuery.trim()}'. Analyze bugs, explain key functions, suggest refactoring, and assess algorithmic complexity.`;
      }

      const res = await fetch(`${API_BASE}/api/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ message: queryPrompt, route: 'github' })
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data.response || data.text || 'Operation completed.');
      } else {
        const errJson = await res.json().catch(() => ({}));
        setErrorMsg(
          errJson.detail || 'Error executing GitHub operation. Ensure your GitHub integration is active.'
        );
      }
    } catch (err: any) {
      console.error('Error in GitHub Workbench', err);
      setErrorMsg(err.message || 'Network or execution error communicating with backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: '960px',
        margin: '28px auto',
        padding: '0 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }}
    >
      {/* Control Panel Card */}
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(16px)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-xl)',
          padding: '28px',
          boxShadow: '0 12px 40px rgba(0, 0, 0, 0.45)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(139, 92, 246, 0.25) 100%)',
                border: '1px solid var(--border-accent)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#a5b4fc',
              }}
            >
              <FolderGit2 size={22} />
            </div>
            <div>
              <h2
                style={{
                  margin: 0,
                  fontSize: '1.25rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-heading)',
                  color: '#ffffff',
                }}
              >
                GitHub Code Workbench
              </h2>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.80rem', color: 'var(--text-muted)' }}>
                Search student repos, inspect source files, or run automated AI code reviews
              </p>
            </div>
          </div>
        </div>

        {/* Action Toggle */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '8px',
            background: 'rgba(2, 6, 23, 0.7)',
            padding: '4px',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            marginBottom: '20px',
          }}
        >
          <button
            type="button"
            onClick={() => setAction('search')}
            className="btn btn-sm"
            style={{
              borderRadius: 'var(--radius-md)',
              background: action === 'search' ? 'var(--primary)' : 'transparent',
              color: action === 'search' ? '#ffffff' : 'var(--text-secondary)',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <Search size={15} />
            <span>Search Repos</span>
          </button>

          <button
            type="button"
            onClick={() => setAction('read')}
            className="btn btn-sm"
            style={{
              borderRadius: 'var(--radius-md)',
              background: action === 'read' ? 'var(--primary)' : 'transparent',
              color: action === 'read' ? '#ffffff' : 'var(--text-secondary)',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <FileText size={15} />
            <span>Read File</span>
          </button>

          <button
            type="button"
            onClick={() => setAction('review')}
            className="btn btn-sm"
            style={{
              borderRadius: 'var(--radius-md)',
              background: action === 'review' ? 'var(--primary)' : 'transparent',
              color: action === 'review' ? '#ffffff' : 'var(--text-secondary)',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <Code size={15} />
            <span>Code Review</span>
          </button>
        </div>

        {/* Inputs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '0.80rem',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}
            >
              {action === 'search' ? 'Search Query / Keyword' : 'Repository (owner/repo)'}
            </label>
            <input
              type="text"
              value={repoQuery}
              onChange={(e) => setRepoQuery(e.target.value)}
              placeholder={action === 'search' ? 'e.g. embedded c microcontroller or machine-learning' : 'e.g. octocat/Hello-World'}
              className="input"
              style={{ width: '100%', fontSize: '0.88rem' }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !loading) executeOperation();
              }}
            />
          </div>

          {action !== 'search' && (
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.80rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                }}
              >
                File Path within Repository
              </label>
              <input
                type="text"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                placeholder="e.g. src/main.py, README.md, or index.js"
                className="input"
                style={{ width: '100%', fontSize: '0.88rem', fontFamily: 'monospace' }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !loading) executeOperation();
                }}
              />
            </div>
          )}

          <button
            type="button"
            onClick={executeOperation}
            disabled={loading || !repoQuery.trim()}
            className="btn btn-primary"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              marginTop: '6px',
              padding: '12px 20px',
              fontWeight: 600,
              fontSize: '0.90rem',
            }}
          >
            {loading ? <Loader2 size={18} className="spin" /> : <Code size={18} />}
            <span>{loading ? 'Analyzing with GitHub MCP...' : 'Run GitHub Action'}</span>
          </button>
        </div>
      </div>

      {/* Error Display */}
      {errorMsg && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-lg)',
            padding: '14px 18px',
            color: '#fca5a5',
            fontSize: '0.88rem',
          }}
        >
          <AlertCircle size={20} color="#ef4444" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Output Console Card */}
      {result && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.85)',
            backdropFilter: 'blur(16px)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-xl)',
            padding: '24px',
            boxShadow: '0 12px 40px rgba(0, 0, 0, 0.45)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '16px',
              paddingBottom: '12px',
              borderBottom: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} color="var(--primary)" />
              <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
                Agent Analysis & Code Result
              </h3>
            </div>
            <button
              type="button"
              onClick={executeOperation}
              disabled={loading}
              className="btn btn-ghost btn-sm"
              title="Re-run analysis"
              style={{ color: 'var(--text-muted)' }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
            </button>
          </div>

          <div
            style={{
              background: 'rgba(2, 6, 23, 0.8)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '20px',
              color: '#e2e8f0',
              fontSize: '0.90rem',
              lineHeight: 1.6,
              overflowX: 'auto',
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
};
