/**
 * src/components/settings/GitHubConnectCard.jsx
 * GitHub OAuth & MCP Integration Card.
 * Allows users to link their GitHub account via OAuth popup for
 * code repository inspection, commit analysis, and assignment reviews.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Unlink,
  RefreshCw,
  Code2,
} from 'lucide-react';
import { endpoints } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';

function GitHubIcon({ size = 18, color = 'currentColor' }) {
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

export function GitHubConnectCard() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [githubLogin, setGithubLogin] = useState(null);

  const checkStatus = useCallback(async () => {
    try {
      setLoading(true);
      const res = await endpoints.getGitHubStatus();
      if (res && res.connected) {
        setIsConnected(true);
        setGithubLogin(res.github_login);
      } else {
        setIsConnected(false);
        setGithubLogin(null);
      }
    } catch {
      setIsConnected(false);
      setGithubLogin(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkStatus();

    // Listen for OAuth completion from popup window
    const handleMessage = (event) => {
      if (event.data && event.data.type === 'GITHUB_AUTH_SUCCESS') {
        setIsConnected(true);
        setGithubLogin(event.data.login || null);
        addToast(
          event.data.login
            ? `Successfully connected GitHub account @${event.data.login}!`
            : 'GitHub account successfully connected!',
          'success'
        );
        checkStatus();
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [checkStatus, addToast]);

  const handleConnect = async () => {
    try {
      setActionLoading(true);
      // Use configured OAuth redirect URI registered with the GitHub application
      const res = await endpoints.getGitHubAuthUrl();
      const authUrl = res?.authorize_url;

      if (!authUrl) {
        const errorDetail =
          typeof res === 'string' && res.includes('<!doctype')
            ? 'Vite proxy needs a quick restart to route /api/auth/github. Please reload your dev server.'
            : (res?.detail || 'Failed to generate GitHub authorization link.');
        throw new Error(errorDetail);
      }

      // Center popup window
      const width = 600;
      const height = 700;
      const left = window.screen.width / 2 - width / 2;
      const top = window.screen.height / 2 - height / 2;

      const popup = window.open(
        authUrl,
        'github_oauth_popup',
        `toolbar=no, location=no, directories=no, status=no, menubar=no, scrollbars=yes, resizable=yes, copyhistory=no, width=${width}, height=${height}, top=${top}, left=${left}`
      );

      // Periodically check if popup closed or if status changed
      const interval = setInterval(async () => {
        if (!popup || popup.closed) {
          clearInterval(interval);
          setActionLoading(false);
          checkStatus();
        }
      }, 1500);
    } catch (err) {
      setActionLoading(false);
      addToast(err.message || 'Could not initiate GitHub connection.', 'error');
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect your GitHub account from StudySync AI?')) {
      return;
    }

    try {
      setActionLoading(true);
      await endpoints.disconnectGitHub();
      setIsConnected(false);
      setGithubLogin(null);
      addToast('GitHub account disconnected.', 'info');
    } catch (err) {
      addToast(err.message || 'Failed to disconnect GitHub account.', 'error');
    } finally {
      setActionLoading(false);
      checkStatus();
    }
  };

  return (
    <div
      style={{
        marginTop: '20px',
        padding: '16px',
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <GitHubIcon size={18} color="#f8fafc" />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600 }}>
              GitHub Copilot & Code MCP
            </h4>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Inspect student repos, review code & lab commits
            </span>
          </div>
        </div>

        {/* Status Badge */}
        {loading ? (
          <div className="badge" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8' }}>
            <RefreshCw size={12} className="spin" style={{ marginRight: '4px' }} /> Checking...
          </div>
        ) : isConnected ? (
          <div
            className="badge"
            style={{
              background: 'rgba(16, 185, 129, 0.15)',
              color: '#34d399',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <CheckCircle2 size={13} />
            <span>Connected {githubLogin ? `@${githubLogin}` : ''}</span>
          </div>
        ) : (
          <div
            className="badge"
            style={{
              background: 'rgba(148, 163, 184, 0.12)',
              color: '#94a3b8',
              border: '1px solid rgba(148, 163, 184, 0.25)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <AlertCircle size={13} />
            <span>Not Connected</span>
          </div>
        )}
      </div>

      <p
        style={{
          fontSize: '0.80rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.45,
          margin: '0 0 14px 0',
        }}
      >
        {isConnected
          ? `Linked to GitHub as @${githubLogin || 'student'}. The AI Copilot can browse your repositories, check lab code, and explain git changes.`
          : 'Connect your GitHub account to enable the AI Copilot to examine project repositories, read code files, and review commits during study sessions.'}
      </p>

      {/* Action Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {isConnected ? (
          <button
            type="button"
            onClick={handleDisconnect}
            disabled={actionLoading}
            className="btn btn-secondary btn-sm"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: '#f87171',
              borderColor: 'rgba(239, 68, 68, 0.3)',
            }}
          >
            <Unlink size={14} />
            <span>{actionLoading ? 'Disconnecting...' : 'Disconnect GitHub'}</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={handleConnect}
            disabled={actionLoading}
            className="btn btn-primary btn-sm"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'linear-gradient(135deg, #24292e 0%, #1f2328 100%)',
              border: '1px solid #444c56',
            }}
          >
            <GitHubIcon size={15} />
            <span>{actionLoading ? 'Opening GitHub...' : 'Connect GitHub Account'}</span>
            <ExternalLink size={13} style={{ opacity: 0.7 }} />
          </button>
        )}

        <button
          type="button"
          onClick={checkStatus}
          disabled={loading || actionLoading}
          className="btn btn-ghost btn-sm"
          title="Refresh connection status"
          style={{ padding: '6px 8px', color: 'var(--text-muted)' }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
        </button>
      </div>
    </div>
  );
}
