/**
 * src/pages/ChatPage.jsx
 * Real-time SSE token-streaming chat interface with voice I/O and markdown formatting.
 */

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send,
  Square,
  Bot,
  User,
  Sparkles,
  RotateCcw,
  Volume2,
  Trash2,
  Cpu,
} from 'lucide-react';
import { streamChatResponse } from '../api/client';
import { AudioPlayer } from '../components/AudioPlayer';
import { VoiceRecorder } from '../components/VoiceRecorder';
import { DocumentSelector } from '../components/DocumentSelector';
import { useToast } from '../context/ToastContext';

export function ChatPage({ initialDocId = 'syllabus' }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Hello! I am your **AI Study Assistant**. Ask me anything about your university syllabus, engineering concepts, lecture notes, or code. You can also pick a specific uploaded PDF or use your voice to ask!",
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState(initialDocId || 'syllabus');

  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);
  const { addToast } = useToast();

  useEffect(() => {
    if (initialDocId) {
      setSelectedDocId(initialDocId);
    }
  }, [initialDocId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const handleSend = async (customPrompt) => {
    const promptToSend = (customPrompt || inputPrompt).trim();
    if (!promptToSend || isStreaming) return;

    // Append user message
    const userMsgId = 'msg-' + Date.now();
    const assistantMsgId = 'msg-' + (Date.now() + 1);

    const newMessages = [
      ...messages,
      { id: userMsgId, role: 'user', content: promptToSend },
      { id: assistantMsgId, role: 'assistant', content: '' },
    ];

    setMessages(newMessages);
    setInputPrompt('');
    setIsStreaming(true);

    // Format conversation history for backend
    const historyPayload = messages
      .filter((m) => m.id !== 'welcome')
      .map((m) => ({ role: m.role, content: m.content }));

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await streamChatResponse({
        prompt: promptToSend,
        docId: selectedDocId,
        conversationHistory: historyPayload,
        signal: abortController.signal,
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, content: m.content + token } : m
            )
          );
        },
        onError: (err) => {
          console.error('Chat stream error:', err);
          addToast(`Error: ${err.message}`, 'error');
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId && !m.content
                ? {
                    ...m,
                    content:
                      `⚠️ *Sorry, an error occurred while generating response: ${err.message || 'Please check backend status or authentication token.'}*`,
                  }
                : m
            )
          );
        },
        onDone: () => {
          setIsStreaming(false);
          abortControllerRef.current = null;
        },
      });
    } catch (err) {
      console.error('Failed to initiate chat stream:', err);
      setIsStreaming(false);
      addToast(`Stream failed: ${err.message}`, 'error');
    }
  };

  const handleStopStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      addToast('Response generation stopped.', 'info');
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          "Conversation cleared. How can I assist your study session now?",
      },
    ]);
    addToast('Chat history cleared.', 'info');
  };

  const samplePrompts = [
    'Explain the concept of Virtual Ground in Op-Amps',
    'Summarize high-yield formulas in linear circuits',
    'Compare Inverting vs Non-Inverting amplifier gains',
    'What are the core review questions for Unit 1?',
  ];

  return (
    <div
      style={{
        maxWidth: '1000px',
        margin: '0 auto',
        padding: '24px 20px',
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 85px)',
      }}
    >
      {/* Top Context & Action Bar */}
      <div
        className="glass-card"
        style={{
          padding: '14px 20px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ minWidth: '280px', flex: 1 }}>
          <DocumentSelector
            selectedDocId={selectedDocId}
            onSelectDocId={setSelectedDocId}
            showLabel={false}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={handleClearHistory}
            className="btn btn-ghost btn-sm"
            title="Clear Chat History"
          >
            <Trash2 size={15} />
            <span>Clear Chat</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div
        className="glass-card"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          marginBottom: '16px',
        }}
      >
        {messages.map((msg) => {
          const isAssistant = msg.role === 'assistant';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                gap: '14px',
                alignItems: 'flex-start',
                flexDirection: isAssistant ? 'row' : 'row-reverse',
              }}
            >
              {/* Avatar Icon */}
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: 'var(--radius-md)',
                  background: isAssistant
                    ? 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)'
                    : 'rgba(255, 255, 255, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  boxShadow: isAssistant ? '0 0 12px var(--primary-glow)' : 'none',
                }}
              >
                {isAssistant ? <Bot size={19} color="#ffffff" /> : <User size={19} color="#cbd5e1" />}
              </div>

              {/* Message Bubble */}
              <div
                style={{
                  maxWidth: '82%',
                  background: isAssistant ? 'var(--bg-card-hover)' : 'var(--primary)',
                  color: '#ffffff',
                  padding: '14px 18px',
                  borderRadius: 'var(--radius-lg)',
                  border: isAssistant ? '1px solid var(--border-subtle)' : 'none',
                  boxShadow: 'var(--shadow-subtle)',
                }}
              >
                {isAssistant ? (
                  <div>
                    {msg.content ? (
                      <div className="markdown-content" style={{ lineHeight: 1.6 }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div className="wave-bars">
                          <div className="wave-bar" />
                          <div className="wave-bar" />
                          <div className="wave-bar" />
                        </div>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          Thinking & generating response...
                        </span>
                      </div>
                    )}

                    {/* Audio TTS Listen Action for Assistant */}
                    {msg.content && (
                      <div
                        style={{
                          marginTop: '12px',
                          paddingTop: '10px',
                          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'flex-start',
                        }}
                      >
                        <AudioPlayer text={msg.content} />
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {msg.content}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompt Chips */}
      {messages.length <= 2 && !isStreaming && (
        <div
          style={{
            display: 'flex',
            gap: '8px',
            overflowX: 'auto',
            paddingBottom: '10px',
            marginBottom: '6px',
          }}
        >
          {samplePrompts.map((sample, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(sample)}
              className="btn btn-secondary btn-sm"
              style={{
                borderRadius: 'var(--radius-full)',
                fontSize: '0.8rem',
                whiteSpace: 'nowrap',
              }}
            >
              <Sparkles size={12} color="var(--primary)" />
              <span>{sample}</span>
            </button>
          ))}
        </div>
      )}

      {/* Input Area */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="glass-card"
        style={{
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          borderRadius: 'var(--radius-xl)',
        }}
      >
        <VoiceRecorder
          onTranscriptionComplete={(text) => {
            setInputPrompt((prev) => (prev ? `${prev} ${text}` : text));
          }}
          isCompact={true}
        />

        <input
          type="text"
          value={inputPrompt}
          onChange={(e) => setInputPrompt(e.target.value)}
          placeholder="Ask anything about your syllabus, theorems, notes..."
          disabled={isStreaming}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: '0.96rem',
            padding: '8px',
          }}
        />

        {isStreaming ? (
          <button
            type="button"
            onClick={handleStopStream}
            className="btn btn-danger btn-sm"
            style={{ borderRadius: 'var(--radius-full)' }}
          >
            <Square size={14} fill="#ffffff" />
            <span>Stop</span>
          </button>
        ) : (
          <button
            type="submit"
            disabled={!inputPrompt.trim()}
            className="btn btn-primary btn-icon"
            style={{ borderRadius: 'var(--radius-full)', width: '38px', height: '38px' }}
          >
            <Send size={16} />
          </button>
        )}
      </form>
    </div>
  );
}
