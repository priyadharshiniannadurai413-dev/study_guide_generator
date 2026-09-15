/**
 * src/components/Navbar.jsx
 * Premium, responsive navigation header with active tab indicator,
 * backend health status, and unified Settings & GitHub MCP modal.
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
  KeyRound,
  FileCheck2,
  X,
  FolderGit2,
  Settings2,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Cpu,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { GitHubConnector } from './github/GitHubConnector';

export function Navbar({ activeTab, setActiveTab }) {
  const { token, updateToken, userName } = useAuth();
  const { addToast } = useToast();
  const [isBackendOnline, setIsBackendOnline] = useState(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState('github'); // 'github' | 'auth'
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
    setIsSettingsOpen(false);
    addToast(
      tokenInput.trim() ? 'Clerk Bearer token configured.' : 'Cleared custom token.',
      'success'
    );
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'chat', label: 'AI Copilot', icon: MessageSquare },
    { id: 'workbench', label: 'GitHub Lab', icon: FolderGit2 },
    { id: 'mcp', label: 'MCP Hub', icon: Cpu },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'pack', label: 'Study Pack', icon: Sparkles },
    { id: 'notes', label: 'Study Notes', icon: BookOpen },
    { id: 'quiz', label: 'MCQ Arena', icon: HelpCircle },
    { id: 'test', label: 'Exam Prep', icon: FileCheck2 },
  ];

  return (
    <>
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          background: 'rgba(10, 13, 20, 0.88)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '0 20px',
          height: '66px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
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
            flexShrink: 0,
            userSelect: 'none',
          }}
        >
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(99, 102, 241, 0.35)',
              transition: 'transform 0.2s ease',
            }}
          >
            <GraduationCap size={22} color="#ffffff" />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontWeight: 800,
                  fontSize: '1.18rem',
                  letterSpacing: '-0.02em',
                  color: '#ffffff',
                }}
              >
                StudySync
              </span>
              <span
                style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  color: '#a5b4fc',
                  background: 'rgba(99, 102, 241, 0.2)',
                  border: '1px solid rgba(99, 102, 241, 0.4)',
                  padding: '1px 6px',
                  borderRadius: '4px',
                }}
              >
                AI
              </span>
            </div>
            <div
              style={{
                fontSize: '0.68rem',
                color: 'var(--text-muted)',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                marginTop: '-2px',
              }}
            >
              Academic Engine
            </div>
          </div>
        </div>

        {/* Center Navigation Tabs Container */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            flex: '1 1 auto',
            justifyContent: 'center',
            minWidth: 0,
            overflow: 'hidden',
          }}
        >
          <nav
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              background: 'rgba(17, 24, 39, 0.75)',
              padding: '4px 5px',
              borderRadius: '9999px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              overflowX: 'auto',
              scrollbarWidth: 'none',
              msOverflowStyle: 'none',
              maxWidth: '100%',
            }}
          >
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    borderRadius: '9999px',
                    padding: '6px 13px',
                    fontSize: '0.82rem',
                    fontWeight: isActive ? 600 : 500,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    color: isActive ? '#ffffff' : 'var(--text-secondary)',
                    background: isActive
                      ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.28) 0%, rgba(168, 85, 247, 0.28) 100%)'
                      : 'transparent',
                    border: isActive
                      ? '1px solid rgba(99, 102, 241, 0.55)'
                      : '1px solid transparent',
                    boxShadow: isActive ? '0 0 14px rgba(99, 102, 241, 0.28)' : 'none',
                    transition: 'all 0.18s ease',
                    outline: 'none',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                      e.currentTarget.style.color = '#ffffff';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text-secondary)';
                    }
                  }}
                >
                  <Icon size={15} color={isActive ? '#a5b4fc' : 'currentColor'} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Right Status & Profile Area */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            flexShrink: 0,
          }}
        >
          {/* Subtle Backend Status Pill */}
          <div
            title={
              isBackendOnline === true
                ? 'FastAPI Backend Online (port 8000)'
                : isBackendOnline === false
                ? 'FastAPI Backend Offline'
                : 'Connecting to Backend...'
            }
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '9999px',
              fontSize: '0.74rem',
              fontWeight: 500,
              background:
                isBackendOnline === true
                  ? 'rgba(16, 185, 129, 0.1)'
                  : isBackendOnline === false
                  ? 'rgba(239, 68, 68, 0.1)'
                  : 'rgba(148, 163, 184, 0.1)',
              color:
                isBackendOnline === true
                  ? '#34d399'
                  : isBackendOnline === false
                  ? '#f87171'
                  : '#94a3b8',
              border: `1px solid ${
                isBackendOnline === true
                  ? 'rgba(16, 185, 129, 0.25)'
                  : isBackendOnline === false
                  ? 'rgba(239, 68, 68, 0.25)'
                  : 'rgba(148, 163, 184, 0.2)'
              }`,
              userSelect: 'none',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor:
                  isBackendOnline === true
                    ? '#10b981'
                    : isBackendOnline === false
                    ? '#ef4444'
                    : '#94a3b8',
                boxShadow:
                  isBackendOnline === true
                    ? '0 0 8px #10b981'
                    : isBackendOnline === false
                    ? '0 0 8px #ef4444'
                    : 'none',
              }}
            />
            <span>{isBackendOnline === true ? 'API Active' : isBackendOnline === false ? 'Offline' : 'Connecting'}</span>
          </div>

          {/* Settings & Integrations Modal Trigger */}
          <button
            onClick={() => setIsSettingsOpen(true)}
            title="Settings & Integrations"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '7px 11px',
              borderRadius: '9px',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#cbd5e1',
              cursor: 'pointer',
              fontSize: '0.80rem',
              fontWeight: 500,
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
              e.currentTarget.style.color = '#ffffff';
              e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
              e.currentTarget.style.color = '#cbd5e1';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            }}
          >
            <Settings2 size={15} color="#a5b4fc" />
            <span style={{ display: 'inline-block' }}>Settings</span>
          </button>

          {/* Auth Controls */}
          <SignedOut>
            <SignInButton mode="modal">
              <button
                className="btn btn-primary btn-sm"
                id="clerk-sign-in-btn"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  borderRadius: '9px',
                }}
              >
                <KeyRound size={14} />
                <span>Sign In</span>
              </button>
            </SignInButton>
          </SignedOut>

          <SignedIn>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <UserButton
                afterSignOutUrl="/"
                appearance={{
                  elements: {
                    avatarBox: {
                      width: '32px',
                      height: '32px',
                      border: '2px solid rgba(99, 102, 241, 0.5)',
                      boxShadow: '0 0 10px rgba(99, 102, 241, 0.25)',
                    },
                  },
                }}
              />
            </div>
          </SignedIn>
        </div>
      </header>

      {/* Modern Settings & Integrations Modal */}
      {isSettingsOpen && (
        <div
          className="modal-overlay"
          onClick={() => setIsSettingsOpen(false)}
          style={{ zIndex: 9999 }}
        >
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              maxWidth: '640px',
              width: '100%',
              padding: '24px',
              borderRadius: '20px',
              background: 'rgba(15, 23, 42, 0.96)',
              backdropFilter: 'blur(24px)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              boxShadow: '0 25px 60px rgba(0, 0, 0, 0.7)',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '16px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                marginBottom: '18px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    padding: '8px',
                    borderRadius: '10px',
                    background: 'rgba(99, 102, 241, 0.15)',
                    color: '#818cf8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Settings2 size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.12rem', fontWeight: 700, color: '#ffffff' }}>
                    Platform Settings & Integrations
                  </h3>
                  <p style={{ margin: '2px 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Configure developer access tokens, MCP tools, and external services
                  </p>
                </div>
              </div>

              <button
                onClick={() => setIsSettingsOpen(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
                onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Tab Controls */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '8px',
                padding: '4px',
                background: 'rgba(3, 7, 18, 0.6)',
                borderRadius: '12px',
                marginBottom: '20px',
                border: '1px solid rgba(255, 255, 255, 0.06)',
              }}
            >
              <button
                type="button"
                onClick={() => setSettingsTab('github')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  borderRadius: '9px',
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: 'none',
                  outline: 'none',
                  transition: 'all 0.15s ease',
                  background:
                    settingsTab === 'github'
                      ? 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)'
                      : 'transparent',
                  color: settingsTab === 'github' ? '#ffffff' : 'var(--text-secondary)',
                  boxShadow:
                    settingsTab === 'github' ? '0 2px 10px rgba(99, 102, 241, 0.35)' : 'none',
                }}
              >
                <FolderGit2 size={16} />
                <span>GitHub MCP Connector</span>
              </button>

              <button
                type="button"
                onClick={() => setSettingsTab('auth')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  borderRadius: '9px',
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: 'none',
                  outline: 'none',
                  transition: 'all 0.15s ease',
                  background:
                    settingsTab === 'auth'
                      ? 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)'
                      : 'transparent',
                  color: settingsTab === 'auth' ? '#ffffff' : 'var(--text-secondary)',
                  boxShadow:
                    settingsTab === 'auth' ? '0 2px 10px rgba(99, 102, 241, 0.35)' : 'none',
                }}
              >
                <ShieldCheck size={16} />
                <span>Session & Token Auth</span>
              </button>
            </div>

            {/* Tab 1: GitHub MCP Connector */}
            {settingsTab === 'github' && (
              <div style={{ animation: 'fadeIn 0.2s ease' }}>
                <GitHubConnector />
              </div>
            )}

            {/* Tab 2: Custom Bearer Session */}
            {settingsTab === 'auth' && (
              <form onSubmit={handleSaveToken} style={{ animation: 'fadeIn 0.2s ease' }}>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: 1.5 }}>
                  The backend API routes authenticate via Clerk JWT Bearer tokens automatically.
                  You can inspect or override a custom session token below:
                </p>

                <label
                  style={{
                    display: 'block',
                    fontSize: '0.80rem',
                    fontWeight: 600,
                    color: '#cbd5e1',
                    marginBottom: '8px',
                  }}
                >
                  Active Bearer Session Token:
                </label>
                <textarea
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Paste custom Clerk session JWT here..."
                  rows={4}
                  className="textarea"
                  style={{
                    fontSize: '0.80rem',
                    fontFamily: 'monospace',
                    marginBottom: '16px',
                    width: '100%',
                    background: 'rgba(3, 7, 18, 0.7)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                  }}
                />

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginTop: '8px',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setTokenInput('');
                      updateToken('');
                      addToast('Custom token cleared.', 'info');
                    }}
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: '0.80rem' }}
                  >
                    Clear Token
                  </button>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      type="button"
                      onClick={() => setIsSettingsOpen(false)}
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '0.80rem' }}
                    >
                      Close
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm"
                      style={{ fontSize: '0.80rem' }}
                    >
                      Save Token
                    </button>
                  </div>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
