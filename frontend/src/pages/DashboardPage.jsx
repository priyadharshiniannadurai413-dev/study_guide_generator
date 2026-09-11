/**
 * src/pages/DashboardPage.jsx
 * Central command hub with quick actions, system stats, and study shortcuts.
 */

import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  MessageSquare,
  FileText,
  BookOpen,
  HelpCircle,
  ArrowRight,
  UploadCloud,
  FolderGit2,
  FileCheck2,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';

export function DashboardPage({ setActiveTab }) {
  const [docCount, setDocCount] = useState(0);
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    const loadStats = async () => {
      try {
        const health = await endpoints.getHealth();
        setBackendStatus(health.status === 'ok' ? 'online' : 'error');
      } catch {
        setBackendStatus('offline');
      }

      try {
        const docs = await endpoints.listDocuments();
        if (Array.isArray(docs)) setDocCount(docs.length);
      } catch {
        // auth or empty
      }
    };

    loadStats();
  }, []);

  const featureCards = [
    {
      title: 'AI Study Copilot',
      description:
        'Ask conceptual questions, explore syllabus units, get step-by-step problem solutions with real-time SSE streaming.',
      icon: MessageSquare,
      color: '#6366f1',
      bgGlow: 'rgba(99, 102, 241, 0.15)',
      action: () => setActiveTab('chat'),
      actionText: 'Launch Copilot',
    },
    {
      title: 'High-Yield Study Notes',
      description:
        'Synthesize executive summaries, core concepts, formulas, theorems, and exam revision points from any document or syllabus.',
      icon: BookOpen,
      color: '#8b5cf6',
      bgGlow: 'rgba(139, 92, 246, 0.15)',
      action: () => setActiveTab('notes'),
      actionText: 'Generate Notes',
    },
    {
      title: 'Interactive MCQ Arena',
      description:
        'Practice with auto-generated multiple-choice questions with 4 distinct options, instant answers, and detailed rationale.',
      icon: HelpCircle,
      color: '#06b6d4',
      bgGlow: 'rgba(6, 182, 212, 0.15)',
      action: () => setActiveTab('quiz'),
      actionText: 'Take Quiz',
    },
    {
      title: 'GitHub Code Workbench',
      description:
        'Inspect student repositories, browse and read source files, check commits, and run automated senior developer code reviews via MCP.',
      icon: FolderGit2,
      color: '#ec4899',
      bgGlow: 'rgba(236, 72, 153, 0.15)',
      action: () => setActiveTab('workbench'),
      actionText: 'Open Workbench',
    },
    {
      title: 'Document Knowledge Vault',
      description:
        'Upload your lecture slides, class notes, and textbook PDFs up to 25MB for dense vector embeddings and isolated retrieval.',
      icon: UploadCloud,
      color: '#10b981',
      bgGlow: 'rgba(16, 185, 129, 0.15)',
      action: () => setActiveTab('documents'),
      actionText: 'Manage Vault',
    },
    {
      title: 'University Exam Prep',
      description:
        'Practice 2-mark conceptual questions with automated AI semantic evaluation, key point rubrics, and detailed scoring feedback.',
      icon: FileCheck2,
      color: '#f59e0b',
      bgGlow: 'rgba(245, 158, 11, 0.15)',
      action: () => setActiveTab('test'),
      actionText: 'Launch Exam Prep',
    },
  ];

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Hero Banner */}
      <div
        className="glass-card"
        style={{
          padding: '40px',
          marginBottom: '32px',
          position: 'relative',
          overflow: 'hidden',
          background:
            'radial-gradient(ellipse at 85% 20%, rgba(99, 102, 241, 0.22) 0%, rgba(17, 24, 39, 0.85) 70%)',
        }}
      >
        <div style={{ position: 'relative', zIndex: 1, maxWidth: '720px' }}>
          <div
            className="badge badge-primary"
            style={{ marginBottom: '14px', padding: '6px 12px' }}
          >
            <Sparkles size={13} />
            <span>AI-Powered University Study Platform</span>
          </div>

          <h1 style={{ marginBottom: '16px', letterSpacing: '-0.03em' }}>
            Elevate Your Academic Mastery with Neural Intelligence
          </h1>

          <p style={{ fontSize: '1.05rem', lineHeight: 1.6, marginBottom: '24px' }}>
            Transform dense lecture notes, course curricula, and textbook PDFs into structured
            revision guides, interactive quizzes, and voice-assisted problem solving.
          </p>

          <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
            <button
              onClick={() => setActiveTab('chat')}
              className="btn btn-primary btn-lg"
            >
              <MessageSquare size={18} />
              <span>Start Learning Session</span>
              <ArrowRight size={16} />
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className="btn btn-secondary btn-lg"
            >
              <FileText size={18} />
              <span>Upload Course Material</span>
            </button>
          </div>
        </div>
      </div>

      {/* Feature Navigation Cards */}
      <h2 style={{ marginBottom: '20px', fontSize: '1.4rem' }}>Study Capabilities & Tools</h2>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))',
          gap: '20px',
        }}
      >
        {featureCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className="glass-card glass-card-hover"
              style={{
                padding: '28px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div
                  style={{
                    width: '48px',
                    height: '48px',
                    borderRadius: 'var(--radius-md)',
                    background: card.bgGlow,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: card.color,
                    marginBottom: '18px',
                  }}
                >
                  <Icon size={24} />
                </div>

                <h3 style={{ marginBottom: '10px' }}>{card.title}</h3>
                <p style={{ fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '24px' }}>
                  {card.description}
                </p>
              </div>

              <button
                onClick={card.action}
                className="btn btn-outline-primary"
                style={{ width: '100%' }}
              >
                <span>{card.actionText}</span>
                <ArrowRight size={15} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
