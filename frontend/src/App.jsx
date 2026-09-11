import React, { useState, useEffect } from 'react';
import { SignIn, SignUp, SignedIn, SignedOut } from '@clerk/clerk-react';
import { GraduationCap, ShieldAlert } from 'lucide-react';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { StudyNotesPage } from './pages/StudyNotesPage';
import { QuizPage } from './pages/QuizPage';
import { TwoMarkTestArena } from './components/study/TwoMarkTestArena';
import { GitHubWorkbench } from './components/github/GitHubWorkbench';
import { MCPConnectorsHub } from './components/mcp/MCPConnectorsHub';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ToastProvider } from './context/ToastContext';
import { AuthProvider } from './context/AuthContext';
import { endpoints } from './api/endpoints';

function GitHubCallbackHandler() {
  const [statusText, setStatusText] = useState('Completing GitHub connection...');
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');

    if (!code || !state) {
      setStatusText('Missing OAuth code or state parameter from GitHub.');
      return;
    }

    endpoints
      .postGitHubCallback({ code, state })
      .then((res) => {
        const login = res?.github_login || 'student';
        setStatusText(`Successfully linked GitHub account @${login}!`);
        setIsDone(true);
        if (window.opener) {
          window.opener.postMessage(
            { type: 'GITHUB_AUTH_SUCCESS', login },
            '*'
          );
        }
        setTimeout(() => window.close(), 1400);
      })
      .catch((err) => {
        setStatusText(`Connection failed: ${err.message || 'Unknown error'}`);
      });
  }, []);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: '#0f172a',
        color: '#f8fafc',
        fontFamily: 'sans-serif',
        textAlign: 'center',
        padding: '24px',
      }}
    >
      <div
        style={{
          background: '#1e293b',
          padding: '36px',
          borderRadius: '14px',
          border: '1px solid #334155',
          maxWidth: '420px',
        }}
      >
        <h2 style={{ color: isDone ? '#34d399' : '#38bdf8', marginTop: 0 }}>
          {isDone ? 'Account Linked!' : 'Connecting to GitHub...'}
        </h2>
        <p style={{ color: '#94a3b8', fontSize: '15px' }}>{statusText}</p>
        {isDone && (
          <p style={{ fontSize: '13px', color: '#64748b' }}>
            This window will close automatically.
          </p>
        )}
      </div>
    </div>
  );
}

function AppContent() {
  const isGitHubCallback = window.location.pathname === '/github/callback';
  if (isGitHubCallback) {
    return <GitHubCallbackHandler />;
  }

  const [activeTab, setActiveTab] = useState(() => {
    const path = window.location.pathname;
    const hash = window.location.hash;
    if (path === '/sign-in' || hash === '#sign-in') return 'sign-in';
    if (path === '/sign-up' || hash === '#sign-up') return 'sign-up';
    return 'dashboard';
  });
  const [selectedDocForStudy, setSelectedDocForStudy] = useState('syllabus');

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      const hash = window.location.hash;
      if (path === '/sign-in' || hash === '#sign-in') setActiveTab('sign-in');
      else if (path === '/sign-up' || hash === '#sign-up') setActiveTab('sign-up');
    };
    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handlePopState);
    };
  }, []);

  const handleSelectDocForStudy = (docId) => {
    setSelectedDocForStudy(docId);
  };

  return (
    <>
      {/* Strict Authentication Gate: Unauthenticated users CANNOT see or access the workspace */}
      <SignedOut>
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background:
              'radial-gradient(ellipse at 50% 25%, rgba(99, 102, 241, 0.15) 0%, rgba(10, 13, 20, 0.98) 75%)',
            padding: '40px 20px',
            color: '#f8fafc',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '16px',
            }}
          >
            <div
              style={{
                width: '46px',
                height: '46px',
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px var(--primary-glow)',
              }}
            >
              <GraduationCap size={26} color="#ffffff" />
            </div>
            <div>
              <h1
                style={{
                  margin: 0,
                  fontSize: '1.6rem',
                  fontWeight: 800,
                  letterSpacing: '-0.02em',
                  background: 'linear-gradient(90deg, #ffffff 0%, #a5b4fc 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                StudySync AI
              </h1>
              <div
                style={{
                  fontSize: '0.72rem',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                Strict Authentication Gate
              </div>
            </div>
          </div>

          <p
            style={{
              maxWidth: '460px',
              textAlign: 'center',
              color: '#94a3b8',
              fontSize: '0.90rem',
              lineHeight: 1.5,
              marginBottom: '28px',
            }}
          >
            Access to this academic workspace is restricted. Please sign in to consult the AI Copilot, examine syllabus materials, review study notes, and run the GitHub Code Workbench.
          </p>

          <SignIn routing="hash" />
        </div>
      </SignedOut>

      {/* Authenticated Workspace */}
      <SignedIn>
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

          <main style={{ flex: 1 }}>
            <ErrorBoundary key={activeTab}>
              {activeTab === 'dashboard' && (
                <DashboardPage setActiveTab={setActiveTab} />
              )}
              {activeTab === 'chat' && (
                <ChatPage initialDocId={selectedDocForStudy} />
              )}
              {activeTab === 'documents' && (
                <DocumentsPage
                  setActiveTab={setActiveTab}
                  onSelectDocForStudy={handleSelectDocForStudy}
                />
              )}
              {activeTab === 'notes' && (
                <StudyNotesPage initialDocId={selectedDocForStudy} />
              )}
              {activeTab === 'quiz' && (
                <QuizPage initialDocId={selectedDocForStudy} />
              )}
              {activeTab === 'test' && (
                <TwoMarkTestArena initialDocId={selectedDocForStudy} />
              )}
              {activeTab === 'workbench' && (
                <GitHubWorkbench />
              )}
              {activeTab === 'mcp' && (
                <MCPConnectorsHub />
              )}
            </ErrorBoundary>
          </main>

          {/* Footer */}
          <footer
            style={{
              borderTop: '1px solid var(--border-subtle)',
              padding: '20px 24px',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.84rem',
              background: 'rgba(10, 13, 20, 0.7)',
            }}
          >
            <div
              style={{
                maxWidth: '1200px',
                margin: '0 auto',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '10px',
              }}
            >
              <div>
                <strong>StudySync AI</strong> &mdash; University Curriculum Assistant & Learning Copilot
              </div>
              <div>
                Powered by Mistral Small &bull; Google Gemini &bull; Groq Whisper &bull; GitHub MCP
              </div>
            </div>
          </footer>
        </div>
      </SignedIn>
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </AuthProvider>
  );
}
