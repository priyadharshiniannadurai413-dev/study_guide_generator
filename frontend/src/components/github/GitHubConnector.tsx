import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, Loader2, Unlink, ExternalLink, ShieldCheck } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { getEffectiveToken, API_BASE } from '../../api/client';

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
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [connectedLogin, setConnectedLogin] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [connecting, setConnecting] = useState<boolean>(false);
  const [disconnecting, setDisconnecting] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const getAuthToken = async (): Promise<string> => {
    try {
      const clerkToken = await getToken();
      if (clerkToken) return clerkToken;
    } catch {
      // Fallback
    }
    return await getEffectiveToken();
  };

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const token = await getAuthToken();
      const res = await fetch(`${API_BASE}/auth/github/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setIsConnected(Boolean(data.connected ?? data.github_connected));
        setConnectedLogin(data.github_login || null);
      } else {
        // Fallback to integrations status
        const fallbackRes = await fetch(`${API_BASE}/api/integrations/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (fallbackRes.ok) {
          const fbData = await fallbackRes.json();
          setIsConnected(Boolean(fbData.github_connected));
          setConnectedLogin(fbData.github_login || null);
        }
      }
    } catch (err) {
      console.error('Failed to fetch GitHub status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();

    // Listen for OAuth completion messages from popup callback
    const handleOAuthMessage = (event: MessageEvent) => {
      if (event.data?.type === 'GITHUB_AUTH_SUCCESS') {
        const login = event.data.login;
        setIsConnected(true);
        setConnectedLogin(login || null);
        setStatusMsg({
          text: `GitHub account connected successfully! ${login ? `(@${login})` : ''}`,
          type: 'success',
        });
        fetchStatus();
      } else if (event.data?.type === 'GITHUB_AUTH_ERROR') {
        setStatusMsg({
          text: `GitHub authorization failed: ${event.data.error || 'Access denied'}`,
          type: 'error',
        });
      }
    };

    window.addEventListener('message', handleOAuthMessage);
    return () => window.removeEventListener('message', handleOAuthMessage);
  }, []);

  const handleOAuthConnect = async () => {
    try {
      setConnecting(true);
      setStatusMsg(null);
      const token = await getAuthToken();
      if (!token) {
        setStatusMsg({ text: 'Please log in to your account first.', type: 'error' });
        return;
      }

      const loginUrl = `${API_BASE}/auth/github/login?token=${encodeURIComponent(token)}&return_to=${encodeURIComponent(window.location.href)}`;

      // Try opening centered popup
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      const popup = window.open(
        loginUrl,
        'github_oauth',
        `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,status=no`
      );

      // If browser blocked popup, fallback to direct page navigation
      if (!popup || popup.closed || typeof popup.closed === 'undefined') {
        window.location.href = loginUrl;
      }
    } catch (err: any) {
      console.error('Error launching GitHub OAuth', err);
      setStatusMsg({ text: `Failed to open GitHub authorization: ${err.message || err}`, type: 'error' });
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect your GitHub integration?')) return;
    try {
      setDisconnecting(true);
      setStatusMsg(null);
      const token = await getAuthToken();
      const res = await fetch(`${API_BASE}/auth/github/disconnect`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setIsConnected(false);
        setConnectedLogin(null);
        setStatusMsg({ text: 'GitHub integration disconnected successfully.', type: 'info' });
      } else {
        // Fallback to legacy delete endpoint
        await fetch(`${API_BASE}/api/integrations/github`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        setIsConnected(false);
        setConnectedLogin(null);
        setStatusMsg({ text: 'GitHub integration disconnected.', type: 'info' });
      }
    } catch (err) {
      console.error('Error disconnecting GitHub', err);
      setStatusMsg({ text: 'Failed to disconnect GitHub account.', type: 'error' });
    } finally {
      setDisconnecting(false);
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
        <span style={{ fontSize: '0.85rem' }}>Checking GitHub OAuth status...</span>
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
      {/* Header */}
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
              GitHub OAuth Integration
            </h3>
            <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Connect repositories for code analysis, commit history, and automated review
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
              gap: '6px',
              padding: '4px 12px',
              borderRadius: '9999px',
              fontSize: '0.78rem',
              fontWeight: 600,
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
              gap: '6px',
              padding: '4px 12px',
              borderRadius: '9999px',
              fontSize: '0.78rem',
              fontWeight: 600,
            }}
          >
            <XCircle size={14} /> Not Connected
          </span>
        )}
      </div>

      {/* Body */}
      <div style={{ marginTop: '16px' }}>
        {statusMsg && (
          <div
            style={{
              marginBottom: '14px',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.82rem',
              background:
                statusMsg.type === 'success'
                  ? 'rgba(16, 185, 129, 0.15)'
                  : statusMsg.type === 'error'
                  ? 'rgba(239, 68, 68, 0.15)'
                  : 'rgba(99, 102, 241, 0.15)',
              color:
                statusMsg.type === 'success'
                  ? '#34d399'
                  : statusMsg.type === 'error'
                  ? '#f87171'
                  : '#a5b4fc',
              border: `1px solid ${
                statusMsg.type === 'success'
                  ? 'rgba(16, 185, 129, 0.3)'
                  : statusMsg.type === 'error'
                  ? 'rgba(239, 68, 68, 0.3)'
                  : 'rgba(99, 102, 241, 0.3)'
              }`,
            }}
          >
            {statusMsg.text}
          </div>
        )}

        {isConnected ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              background: 'rgba(2, 6, 23, 0.6)',
              padding: '16px',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} color="#34d399" />
                <span style={{ fontSize: '0.88rem', fontWeight: 600, color: '#f8fafc' }}>
                  Authenticated as @{connectedLogin || 'user'}
                </span>
              </div>
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={disconnecting}
                className="btn btn-secondary btn-sm"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: '#fb7185',
                  borderColor: 'rgba(244, 63, 94, 0.3)',
                  whiteSpace: 'nowrap',
                  cursor: disconnecting ? 'not-allowed' : 'pointer',
                }}
              >
                {disconnecting ? <Loader2 size={14} className="spin" /> : <Unlink size={14} />}
                {disconnecting ? 'Disconnecting...' : 'Disconnect'}
              </button>
            </div>
            <p style={{ margin: 0, fontSize: '0.80rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Your GitHub OAuth token is safely stored encrypted at rest with Fernet in MongoDB and automatically bound to your authenticated Clerk user session for all agent tools.
            </p>
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <p style={{ margin: 0, fontSize: '0.84rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Authorize StudyGenie via GitHub OAuth to allow your AI Copilot to explore repository code, read assignments, and track commit histories without manually generating or copying tokens.
            </p>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '0.78rem',
                color: '#64748b',
              }}
            >
              <ShieldCheck size={16} color="#818cf8" />
              <span>Direct OAuth 2.0 flow &bull; Encrypted storage in MongoDB &bull; No manual PAT required</span>
            </div>

            <div>
              <button
                type="button"
                onClick={handleOAuthConnect}
                disabled={connecting}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '10px',
                  padding: '10px 20px',
                  borderRadius: 'var(--radius-md)',
                  background: '#24292f',
                  color: '#ffffff',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  fontSize: '0.88rem',
                  fontWeight: 600,
                  cursor: connecting ? 'not-allowed' : 'pointer',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
                  transition: 'background 0.2s, transform 0.1s',
                }}
                onMouseOver={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#2f363d')}
                onMouseOut={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#24292f')}
              >
                {connecting ? (
                  <Loader2 size={18} className="spin" />
                ) : (
                  <GitHubIcon size={18} color="#ffffff" />
                )}
                {connecting ? 'Connecting...' : 'Connect with GitHub'}
                <ExternalLink size={14} style={{ opacity: 0.7 }} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
