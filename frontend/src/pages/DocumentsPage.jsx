/**
 * src/pages/DocumentsPage.jsx
 * Document Knowledge Vault - Drag-and-drop PDF upload, vector indexing, and deletion.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  Trash2,
  BookOpen,
  HelpCircle,
  Clock,
  Layers,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { useToast } from '../context/ToastContext';

export function DocumentsPage({ setActiveTab, onSelectDocForStudy }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const { addToast } = useToast();

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const docs = await endpoints.listDocuments();
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (err) {
      console.warn('Could not load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      addToast('Only PDF documents are supported.', 'error');
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      addToast('File exceeds maximum size of 25MB.', 'error');
      return;
    }

    try {
      setUploading(true);
      const res = await endpoints.uploadDocument(file);
      addToast(`Indexed "${res.filename}" with ${res.total_chunks} chunks!`, 'success');
      await loadDocuments();
    } catch (err) {
      console.error('Upload failed:', err);
      addToast(`Upload failed: ${err.message}`, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) return;

    try {
      await endpoints.deleteDocument(docId);
      addToast(`Document "${filename}" deleted.`, 'success');
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
    } catch (err) {
      console.error('Delete failed:', err);
      addToast(`Failed to delete document: ${err.message}`, 'error');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return 'Recently';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ marginBottom: '8px' }}>Document Knowledge Vault</h1>
        <p style={{ fontSize: '1.05rem' }}>
          Upload your lecture notes, textbook chapters, and assignment PDFs. All documents are
          partitioned to your user account and converted to dense vector embeddings for RAG.
        </p>
      </div>

      {/* Upload Drag & Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className="glass-card"
        style={{
          padding: '48px 24px',
          textAlign: 'center',
          border: `2px dashed ${dragActive ? 'var(--primary)' : 'var(--border-light)'}`,
          backgroundColor: dragActive ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg-card)',
          borderRadius: 'var(--radius-xl)',
          marginBottom: '36px',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
        }}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
          }}
        />

        <div
          style={{
            width: '64px',
            height: '64px',
            borderRadius: 'var(--radius-full)',
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto',
            color: 'var(--primary)',
          }}
        >
          {uploading ? (
            <Loader2 size={32} style={{ animation: 'spin 1.2s linear infinite' }} />
          ) : (
            <UploadCloud size={32} />
          )}
        </div>

        <h3 style={{ marginBottom: '8px' }}>
          {uploading ? 'Processing & Indexing Document Chunks...' : 'Upload Academic PDF'}
        </h3>
        <p style={{ fontSize: '0.92rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Drag and drop your lecture slides or syllabus PDF here, or click to browse (Max 25MB)
        </p>

        <button
          type="button"
          disabled={uploading}
          className="btn btn-primary btn-sm"
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current?.click();
          }}
        >
          {uploading ? 'Embedding Chunks...' : 'Choose PDF File'}
        </button>
      </div>

      {/* Document Library Table / List */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
        <h2>Indexed Documents ({documents.length})</h2>
        <button onClick={loadDocuments} className="btn btn-secondary btn-sm">
          Refresh List
        </button>
      </div>

      {loading ? (
        <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
          <div>Loading knowledge vault...</div>
        </div>
      ) : documents.length === 0 ? (
        <div
          className="glass-card"
          style={{ padding: '48px', textAlign: 'center', color: 'var(--text-secondary)' }}
        >
          <FileText size={42} color="var(--text-muted)" style={{ margin: '0 auto 14px' }} />
          <h3 style={{ marginBottom: '8px' }}>No documents uploaded yet</h3>
          <p style={{ fontSize: '0.9rem', maxWidth: '440px', margin: '0 auto 20px' }}>
            Ingest your course PDFs above, or use the built-in Global Syllabus to generate study
            notes and MCQs right now!
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {documents.map((doc) => (
            <div
              key={doc.doc_id}
              className="glass-card glass-card-hover"
              style={{
                padding: '20px 24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div
                  style={{
                    width: '46px',
                    height: '46px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(99, 102, 241, 0.12)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--primary)',
                  }}
                >
                  <FileText size={24} />
                </div>
                <div>
                  <h4 style={{ marginBottom: '4px' }}>{doc.filename}</h4>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '14px',
                      fontSize: '0.82rem',
                      color: 'var(--text-muted)',
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Layers size={13} />
                      {doc.chunk_count} vector chunks
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={13} />
                      {formatDate(doc.created_at)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  onClick={() => {
                    if (onSelectDocForStudy) onSelectDocForStudy(doc.doc_id);
                    setActiveTab('notes');
                  }}
                  className="btn btn-secondary btn-sm"
                  title="Generate Study Notes from this document"
                >
                  <BookOpen size={14} color="var(--secondary)" />
                  <span>Notes</span>
                </button>

                <button
                  onClick={() => {
                    if (onSelectDocForStudy) onSelectDocForStudy(doc.doc_id);
                    setActiveTab('quiz');
                  }}
                  className="btn btn-secondary btn-sm"
                  title="Generate MCQ Quiz from this document"
                >
                  <HelpCircle size={14} color="var(--cyan)" />
                  <span>Quiz</span>
                </button>

                <button
                  onClick={() => handleDelete(doc.doc_id, doc.filename)}
                  className="btn btn-danger btn-sm btn-icon"
                  title="Delete Document"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
