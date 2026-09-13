import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, Key, Loader2, Unlink, ExternalLink } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { API_BASE, getEffectiveToken } from '../../api/client';

function GitHubIcon({ size = 22, color = '#ffffff' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

export const GitHubConnectorCard: React.FC = () => {
  const { getToken } = useAuth();
  const [pat, setPat] = useState('');
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [githubLogin, setGithubLogin] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);

  const checkStatus = async () => {
    try {
      setLoading(true);
      const token = await getEffectiveToken();
      const res = await fetch(`${API_BASE}/api/integrations/status`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setIsConnected(Boolean(data.github_connected));
        setGithubLogin(data.github_login || '');
      }
    } catch (err) {
      console.error('Failed to fetch GitHub status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pat.trim()) return;
    try {
      setSaving(true);
      const token = await getToken();
      const res = await fetch(`${API_BASE}/api/integrations/github`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ github_pat: pat.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        setIsConnected(true);
        setGithubLogin(data.github_login || '');
        setPat('');
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || 'Invalid GitHub Token or connection failed.');
      }
    } catch (err) {
      console.error('Connection error', err);
      alert('Connection error occurred while contacting backend.');
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      setSaving(true);
      const token = await getToken();
      const res = await fetch(`${API_BASE}/api/integrations/github`, {
        method: 'DELETE',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        setIsConnected(false);
        setGithubLogin('');
      }
    } catch (err) {
      console.error('Disconnect error', err);
    } finally {
      setSaving(false);
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
                background: 'rgba(30, 41, 59, 0.8)',
                borderRadius: '12px',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <GitHubIcon size={22} color="#ffffff" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                GitHub MCP Connector
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                @modelcontextprotocol/server-github
              </p>
            </div>
          </div>
          {loading ? (
            <Loader2 size={18} style={{ animation: 'spin 1s linear infinite', color: '#94a3b8' }} />
          ) : isConnected ? (
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
                border: '1px solid rgba(5, 150, 105, 0.4)',
              }}
            >
              <CheckCircle2 size={14} /> Active {githubLogin ? `(@${githubLogin})` : ''}
            </span>
          ) : (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '4px 10px',
                borderRadius: '999px',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: 'rgba(136, 19, 55, 0.5)',
                color: '#fb7185',
                border: '1px solid rgba(225, 29, 72, 0.4)',
              }}
            >
              <XCircle size={14} /> Disconnected
            </span>
          )}
        </div>

        <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '16px 0', lineHeight: 1.5 }}>
          Enables your AI Copilot to search private repositories, read assignment source files, and execute automated code reviews on your behalf.
        </p>

        {isConnected ? (
          <div
            style={{
              background: 'rgba(2, 6, 23, 0.8)',
              padding: '16px',
              borderRadius: '12px',
              border: '1px solid rgba(51, 65, 85, 0.5)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#cbd5e1' }}>
                Encrypted Token Active {githubLogin ? `(@${githubLogin})` : ''}
              </span>
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={saving}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: '#f87171',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  transition: 'background 0.2s',
                }}
              >
                <Unlink size={14} /> Disconnect
              </button>
            </div>
            <p style={{ margin: 0, fontSize: '0.72rem', color: '#64748b' }}>
              Tools active: <code style={{ color: '#93c5fd' }}>search_repositories</code>, <code style={{ color: '#93c5fd' }}>get_file_contents</code>, <code style={{ color: '#93c5fd' }}>list_commits</code>.
            </p>
          </div>
        ) : (
          <form onSubmit={handleConnect} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  color: '#cbd5e1',
                  marginBottom: '6px',
                }}
              >
                Personal Access Token (PAT)
              </label>
              <div style={{ position: 'relative' }}>
                <Key
                  size={16}
                  style={{
                    position: 'absolute',
                    left: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: '#64748b',
                  }}
                />
                <input
                  type="password"
                  value={pat}
                  onChange={(e) => setPat(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  style={{
                    width: '100%',
                    padding: '10px 12px 10px 36px',
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
            </div>
            <a
              href="https://github.com/settings/tokens"
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.74rem',
                color: '#818cf8',
                textDecoration: 'none',
              }}
            >
              Generate classic token with <code style={{ color: '#c7d2fe', padding: '1px 4px' }}>repo</code> & <code style={{ color: '#c7d2fe', padding: '1px 4px' }}>read:user</code> scopes
              <ExternalLink size={12} />
            </a>
            <button
              type="submit"
              disabled={saving || !pat.trim()}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '10px 16px',
                background: '#4f46e5',
                color: '#ffffff',
                fontSize: '0.82rem',
                fontWeight: 600,
                borderRadius: '8px',
                border: 'none',
                cursor: saving || !pat.trim() ? 'not-allowed' : 'pointer',
                opacity: saving || !pat.trim() ? 0.6 : 1,
                transition: 'background 0.2s ease',
              }}
            >
              {saving ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : null}
              Save & Activate GitHub MCP
            </button>
          </form>
        )}
      </div>

      <div
        style={{
          paddingTop: '16px',
          marginTop: '24px',
          borderTop: '1px solid rgba(51, 65, 85, 0.6)',
          fontSize: '0.72rem',
          color: '#64748b',
        }}
      >
        Transport: <strong style={{ color: '#94a3b8' }}>Stdio Process (Isolated per User)</strong>
      </div>
    </div>
  );
};
