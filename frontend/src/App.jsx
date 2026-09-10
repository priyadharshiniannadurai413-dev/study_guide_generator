/**
 * src/App.jsx
 * Main Application Shell coordinating tabs, auth, and notifications.
 */

import React, { useState, useEffect } from 'react';
import { SignIn, SignUp } from '@clerk/clerk-react';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { StudyNotesPage } from './pages/StudyNotesPage';
import { QuizPage } from './pages/QuizPage';
import { ToastProvider } from './context/ToastContext';
import { AuthProvider } from './context/AuthContext';

function AppContent() {
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
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main style={{ flex: 1 }}>
        {activeTab === 'sign-in' && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: 'calc(100vh - 160px)',
              padding: '30px 20px',
            }}
          >
            <SignIn routing="hash" />
          </div>
        )}
        {activeTab === 'sign-up' && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: 'calc(100vh - 160px)',
              padding: '30px 20px',
            }}
          >
            <SignUp routing="hash" />
          </div>
        )}
        {activeTab === 'dashboard' && <DashboardPage setActiveTab={setActiveTab} />}
        {activeTab === 'chat' && <ChatPage />}
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
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <strong>StudySync AI</strong> &mdash; University Curriculum Assistant & Learning Copilot
          </div>
          <div>
            Powered by Mistral Small &bull; Google Gemini &bull; Groq Whisper &bull; Edge-TTS
          </div>
        </div>
      </footer>
    </div>
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
