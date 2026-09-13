import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, Loader2, Unlink, ExternalLink, ShieldCheck } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { API_BASE, getEffectiveToken } from '../../api/client';
import { endpoints } from '../../api/endpoints';

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
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [githubLogin, setGithubLogin] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [connecting, setConnecting] = useState<boolean>(false);
  const [disconnecting, setDisconnecting] = useState<boolean>(false);

  const getAuthToken = async (): Promise<string> => {
    try {
      const clerkToken = await getToken();
      if (clerkToken) return clerkToken;
    } catch {
      // Fallback
    }
    return await getEffectiveToken();
  };

  const checkStatus = async () => {
    try {
      setLoading(true);
      const token = await getAuthToken();
      const res = await fetch(`${API_BASE}/auth/github/status`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setIsConnected(Boolean(data.connected ?? data.github_connected));
        setGithubLogin(data.github_login || '');
      } else {
        const fallbackRes = await fetch(`${API_BASE}/api/integrations/status`, {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        if (fallbackRes.ok) {
          const data = await fallbackRes.json();
          setIsConnected(Boolean(data.github_connected));
          setGithubLogin(data.github_login || '');
        }
      }
    } catch (err) {
      console.error('Failed to fetch GitHub status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();

    const handleOAuthMessage = (event: MessageEvent) => {
      if (event.data?.type === 'GITHUB_AUTH_SUCCESS') {
        const login = event.data.login || '';
        setIsConnected(true);
        setGithubLogin(login);
        checkStatus();
      }
    };

    window.addEventListener('message', handleOAuthMessage);
    return () => window.removeEventListener('message', handleOAuthMessage);
  }, []);

  const handleOAuthConnect = async () => {
    try {
      setConnecting(true);

      // 1. Try direct API authorize URL
      try {
        const res = await endpoints.getGitHubAuthUrl({
          returnTo: window.location.href,
        });
        if (res && res.authorize_url) {
          const width = 600;
          const height = 700;
          const left = window.screenX + (window.outerWidth - width) / 2;
          const top = window.screenY + (window.outerHeight - height) / 2;
          const popup = window.open(
            res.authorize_url,
            'github_oauth',
            `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,status=no`
          );
          if (!popup || popup.closed || typeof popup.closed === 'undefined') {
            window.location.href = res.authorize_url;
          }
          return;
        }
      } catch (authErr: any) {
        console.warn('API getGitHubAuthUrl fallback:', authErr);
      }

      // 2. Fallback: navigate directly to login URL
      const token = await getAuthToken();
      if (!token) {
        alert('Please log in first.');
        return;
      }

      const loginUrl = `${API_BASE}/auth/github/login?token=${encodeURIComponent(token)}&return_to=${encodeURIComponent(window.location.href)}`;
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      const popup = window.open(
        loginUrl,
        'github_oauth',
        `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,status=no`
      );

      if (!popup || popup.closed || typeof popup.closed === 'undefined') {
        window.location.href = loginUrl;
      }
    } catch (err: any) {
      console.error('Connection error', err);
      alert('Error launching GitHub authorization.');
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect your GitHub MCP integration?')) return;
    try {
      setDisconnecting(true);
      const token = await getAuthToken();
      const res = await fetch(`${API_BASE}/auth/github/disconnect`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        setIsConnected(false);
        setGithubLogin('');
      } else {
        await fetch(`${API_BASE}/api/integrations/github`, {
          method: 'DELETE',
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        setIsConnected(false);
        setGithubLogin('');
      }
    } catch (err) {
      console.error('Disconnect error', err);
    } finally {
      setDisconnecting(false);
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
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ShieldCheck size={16} color="#34d399" />
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#cbd5e1' }}>
                  OAuth Token Active {githubLogin ? `(@${githubLogin})` : ''}
                </span>
              </div>
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={disconnecting}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: '#f87171',
                  background: 'transparent',
                  border: 'none',
                  cursor: disconnecting ? 'not-allowed' : 'pointer',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  transition: 'background 0.2s',
                }}
              >
                {disconnecting ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Unlink size={14} />}
                {disconnecting ? 'Disconnecting...' : 'Disconnect'}
              </button>
            </div>
            <p style={{ margin: 0, fontSize: '0.72rem', color: '#64748b' }}>
              Tools active: <code style={{ color: '#93c5fd' }}>search_repositories</code>, <code style={{ color: '#93c5fd' }}>get_file_contents</code>, <code style={{ color: '#93c5fd' }}>list_commits</code>.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.75rem',
                color: '#64748b',
              }}
            >
              <ShieldCheck size={15} color="#818cf8" />
              <span>Standard OAuth 2.0 authorization with encrypted token storage.</span>
            </div>
            <button
              type="button"
              onClick={handleOAuthConnect}
              disabled={connecting}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '10px 16px',
                background: '#24292f',
                color: '#ffffff',
                fontSize: '0.82rem',
                fontWeight: 600,
                borderRadius: '8px',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                cursor: connecting ? 'not-allowed' : 'pointer',
                opacity: connecting ? 0.7 : 1,
                transition: 'background 0.2s ease',
              }}
            >
              {connecting ? (
                <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
              ) : (
                <GitHubIcon size={16} color="#ffffff" />
              )}
              {connecting ? 'Connecting...' : 'Connect with GitHub'}
              <ExternalLink size={12} style={{ opacity: 0.7 }} />
            </button>
          </div>
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
