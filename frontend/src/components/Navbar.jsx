/**
 * src/components/Navbar.jsx
 * Top navigation header with active tab indicator, backend health status,
 * and authentication configuration modal.
 */

import React, { useState, useEffect } from 'react';
import {
  SignedIn,
  SignedOut,
  SignInButton,
  UserButton,
} from '@clerk/clerk-react';
import {
  GraduationCap,
  MessageSquare,
  FileText,
  BookOpen,
  HelpCircle,
  LayoutDashboard,
  ShieldCheck,
  KeyRound,
  X,
  Radio,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export function Navbar({ activeTab, setActiveTab }) {
  const { token, updateToken, isDevMode, userName } = useAuth();
  const { addToast } = useToast();
  const [isBackendOnline, setIsBackendOnline] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [tokenInput, setTokenInput] = useState(token || '');

  // Periodic health check
  useEffect(() => {
    let isMounted = true;
    const checkServer = async () => {
      try {
        const res = await endpoints.getHealth();
        if (isMounted) setIsBackendOnline(res?.status === 'ok');
      } catch {
        if (isMounted) setIsBackendOnline(false);
      }
    };

    checkServer();
    const interval = setInterval(checkServer, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSaveToken = (e) => {
    e.preventDefault();
    updateToken(tokenInput.trim());
    setIsAuthModalOpen(false);
    addToast(
      tokenInput.trim() ? 'Auth Bearer token updated.' : 'Cleared custom token.',
      'success'
    );
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'chat', label: 'AI Copilot', icon: MessageSquare },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'notes', label: 'Study Notes', icon: BookOpen },
    { id: 'quiz', label: 'MCQ Arena', icon: HelpCircle },
  ];

  return (
    <>
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          background: 'rgba(10, 13, 20, 0.82)',
          backdropFilter: 'blur(16px)',
          borderBottom: '1px solid var(--border-subtle)',
          padding: '0 24px',
          height: '70px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Brand Logo */}
        <div
          onClick={() => setActiveTab('dashboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            cursor: 'pointer',
          }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px var(--primary-glow)',
            }}
          >
            <GraduationCap size={24} color="#ffffff" />
          </div>
          <div>
            <div
              style={{
                fontFamily: 'var(--font-heading)',
                fontWeight: 800,
                fontSize: '1.25rem',
                letterSpacing: '-0.03em',
                background: 'linear-gradient(90deg, #ffffff 0%, #a5b4fc 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              StudySync AI
            </div>
            <div
              style={{
                fontSize: '0.72rem',
                color: 'var(--text-muted)',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                marginTop: '-2px',
              }}
            >
              Curriculum & Learning Engine
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(17, 24, 39, 0.6)',
            padding: '4px',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className="btn btn-ghost btn-sm"
                style={{
                  borderRadius: 'var(--radius-full)',
                  padding: '8px 16px',
                  color: isActive ? '#ffffff' : 'var(--text-secondary)',
                  background: isActive
                    ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.3) 0%, rgba(139, 92, 246, 0.3) 100%)'
                    : 'transparent',
                  border: isActive ? '1px solid var(--border-accent)' : '1px solid transparent',
                  boxShadow: isActive ? '0 0 14px var(--primary-glow)' : 'none',
                }}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Status & Auth Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {/* Backend Status Indicator */}
          <div
            className="badge"
            style={{
              background:
                isBackendOnline === true
                  ? 'rgba(16, 185, 129, 0.12)'
                  : isBackendOnline === false
                  ? 'rgba(239, 68, 68, 0.12)'
                  : 'rgba(148, 163, 184, 0.12)',
              color:
                isBackendOnline === true
                  ? '#34d399'
                  : isBackendOnline === false
                  ? '#f87171'
                  : '#94a3b8',
              border: `1px solid ${
                isBackendOnline === true
                  ? 'rgba(16, 185, 129, 0.3)'
                  : isBackendOnline === false
                  ? 'rgba(239, 68, 68, 0.3)'
                  : 'rgba(148, 163, 184, 0.3)'
              }`,
            }}
            title={
              isBackendOnline === true
                ? 'Backend connected on port 8000'
                : 'Backend unreachable on port 8000'
            }
          >
            <span
              className={`status-dot ${isBackendOnline ? 'online pulsing' : ''}`}
              style={{
                backgroundColor:
                  isBackendOnline === true
                    ? 'var(--success)'
                    : isBackendOnline === false
                    ? 'var(--error)'
                    : 'var(--text-muted)',
              }}
            />
            {isBackendOnline === true
              ? 'FastAPI 8000'
              : isBackendOnline === false
              ? 'Offline'
              : 'Connecting...'}
          </div>

          {/* Clerk Authentication Controls */}
          <SignedOut>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <SignInButton mode="modal">
                <button
                  className="btn btn-primary btn-sm"
                  id="clerk-sign-in-btn"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '7px 16px',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                  }}
                >
                  <KeyRound size={15} />
                  <span>Sign In</span>
                </button>
              </SignInButton>

              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="btn btn-ghost btn-sm"
                title="Dev Token / Settings"
                style={{
                  padding: '6px 10px',
                  color: 'var(--text-muted)',
                }}
              >
                <ShieldCheck size={16} />
              </button>
            </div>
          </SignedOut>

          <SignedIn>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-end',
                  lineHeight: 1.2,
                }}
              >
                <span
                  style={{
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    maxWidth: '130px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {userName}
                </span>
                <span
                  style={{
                    fontSize: '0.70rem',
                    color: '#34d399',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: '#10b981',
                      display: 'inline-block',
                    }}
                  />
                  Clerk Verified
                </span>
              </div>

              <UserButton
                afterSignOutUrl="/"
                appearance={{
                  elements: {
                    avatarBox: {
                      width: '34px',
                      height: '34px',
                      border: '2px solid var(--border-accent)',
                    },
                  },
                }}
              />

              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="btn btn-ghost btn-sm"
                title="Dev Token / Settings"
                style={{
                  padding: '6px 8px',
                  color: 'var(--text-muted)',
                }}
              >
                <ShieldCheck size={16} />
              </button>
            </div>
          </SignedIn>
        </div>
      </header>

      {/* Auth Token Configuration Modal */}
      {isAuthModalOpen && (
        <div className="modal-overlay" onClick={() => setIsAuthModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '18px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShieldCheck size={22} color="var(--primary)" />
                <h3 style={{ margin: 0 }}>Authentication Settings</h3>
              </div>
              <button
                onClick={() => setIsAuthModalOpen(false)}
                className="btn btn-ghost btn-icon"
              >
                <X size={18} />
              </button>
            </div>

            <p style={{ fontSize: '0.88rem', marginBottom: '18px' }}>
              The backend routes are protected by Clerk JWT authentication. You can paste a valid
              Clerk session JWT below, or test directly with the backend.
            </p>

            <form onSubmit={handleSaveToken}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '8px',
                }}
              >
                Clerk Bearer Session Token:
              </label>
              <textarea
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Paste your Clerk session JWT here (ey...)"
                rows={4}
                className="textarea"
                style={{
                  fontSize: '0.82rem',
                  fontFamily: 'monospace',
                  marginBottom: '16px',
                }}
              />

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: '12px',
                }}
              >
                <button
                  type="button"
                  onClick={() => {
                    setTokenInput('');
                    updateToken('');
                    addToast('Token cleared.', 'info');
                  }}
                  className="btn btn-ghost btn-sm"
                >
                  Clear Token
                </button>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    type="button"
                    onClick={() => setIsAuthModalOpen(false)}
                    className="btn btn-secondary btn-sm"
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary btn-sm">
                    Save Token
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
