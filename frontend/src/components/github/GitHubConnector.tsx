import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, Key, Loader2, Unlink } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { getStoredToken, API_BASE } from '../../api/client';

function GitHubIcon({ size = 20, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
    </svg>
  );
}

export const GitHubConnector: React.FC = () => {
  const { getToken } = useAuth();
  const [pat, setPat] = useState('');
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [connectedLogin, setConnectedLogin] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const getAuthToken = async (): Promise<string> => {
    try {
      const clerkToken = await getToken();
      if (clerkToken) return clerkToken;
    } catch {
      // Fallback
    }
    return getStoredToken();
  };

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const token = await getAuthToken();
      const res = await fetch(`${API_BASE}/api/integrations/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIsConnected(Boolean(data.github_connected));
        setConnectedLogin(data.github_login || null);
      }
    } catch (err) {
      console.error('Failed to fetch status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pat.trim()) return;
    try {
      setSaving(true);
      setStatusMsg(null);
      const token = await getAuthToken();
      const res = await fetch(`${API_BASE}/api/integrations/github`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ github_pat: pat.trim() })
      });
      if (res.ok) {
        const data = await res.json();
        setIsConnected(true);
        setConnectedLogin(data.github_login || null);
        setPat('');
        setStatusMsg('GitHub Personal Access Token configured successfully!');
      } else {
        const errJson = await res.json().catch(() => ({}));
        alert(errJson.detail || 'Failed to save GitHub PAT');
      }
    } catch (err) {
      console.error('Error connecting GitHub', err);
      alert('Network error connecting GitHub.');
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect your GitHub integration?')) return;
    try {
      setSaving(true);
      setStatusMsg(null);
      const token = await getAuthToken();
      const res = await fetch(`${API_BASE}/api/integrations/github`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setIsConnected(false);
        setConnectedLogin(null);
        setStatusMsg('GitHub integration disconnected.');
      }
    } catch (err) {
      console.error('Error disconnecting', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          color: 'var(--text-secondary)',
          padding: '20px',
          background: 'rgba(15, 23, 42, 0.65)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
        }}
      >
        <Loader2 size={18} className="spin" />
        <span style={{ fontSize: '0.85rem' }}>Checking GitHub integration status...</span>
      </div>
    );
  }

  return (
    <div
      style={{
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-xl)',
        padding: '24px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35)',
        marginTop: '16px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingBottom: '16px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              padding: '8px',
              background: 'rgba(255, 255, 255, 0.08)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <GitHubIcon size={22} color="#ffffff" />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#ffffff' }}>
              GitHub MCP Connector
            </h3>
            <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Connect your repositories for code review and lab analysis
            </p>
          </div>
        </div>

        {isConnected ? (
          <span
            className="badge"
            style={{
              background: 'rgba(16, 185, 129, 0.15)',
              color: '#34d399',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '9999px',
              fontSize: '0.75rem',
            }}
          >
            <CheckCircle2 size={14} /> Connected {connectedLogin ? `@${connectedLogin}` : ''}
          </span>
        ) : (
          <span
            className="badge"
            style={{
              background: 'rgba(244, 63, 94, 0.15)',
              color: '#fb7185',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '9999px',
              fontSize: '0.75rem',
            }}
          >
            <XCircle size={14} /> Not Configured
          </span>
        )}
      </div>

      <div style={{ marginTop: '16px' }}>
        {statusMsg && (
          <div
            style={{
              marginBottom: '12px',
              padding: '8px 12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.80rem',
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#a5b4fc',
              border: '1px solid rgba(99, 102, 241, 0.3)',
            }}
          >
            {statusMsg}
          </div>
        )}

        {isConnected ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(2, 6, 23, 0.6)',
              padding: '16px',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-subtle)',
              gap: '12px',
            }}
          >
            <p style={{ margin: 0, fontSize: '0.85rem', color: '#cbd5e1' }}>
              Your GitHub access token is encrypted at rest with Fernet and active for agent tools.
            </p>
            <button
              type="button"
              onClick={handleDisconnect}
              disabled={saving}
              className="btn btn-secondary btn-sm"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                color: '#fb7185',
                borderColor: 'rgba(244, 63, 94, 0.3)',
                whiteSpace: 'nowrap',
              }}
            >
              <Unlink size={14} />
              {saving ? 'Disconnecting...' : 'Disconnect'}
            </button>
          </div>
        ) : (
          <form onSubmit={handleConnect} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <label style={{ fontSize: '0.80rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
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
                  color: 'var(--text-muted)',
                }}
              />
              <input
                type="password"
                value={pat}
                onChange={(e) => setPat(e.target.value)}
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                required
                className="input"
                style={{
                  width: '100%',
                  paddingLeft: '36px',
                  fontSize: '0.85rem',
                  fontFamily: 'monospace',
                }}
              />
            </div>
            <p style={{ margin: '2px 0 6px 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Generate a classic or fine-grained token on GitHub with <code>repo</code> and <code>read:user</code> scopes.
            </p>
            <button
              type="submit"
              disabled={saving || !pat.trim()}
              className="btn btn-primary btn-sm"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '9px 16px',
                fontWeight: 600,
              }}
            >
              {saving ? <Loader2 size={16} className="spin" /> : <Key size={15} />}
              Save & Activate Connector
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
