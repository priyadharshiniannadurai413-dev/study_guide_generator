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
  const [uploadPhase, setUploadPhase] = useState('idle'); // 'idle' | 'uploading' | 'indexing' | 'complete' | 'error'
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadFileName, setUploadFileName] = useState('');
  const [uploadFileSize, setUploadFileSize] = useState('');
  const [uploadStatusText, setUploadStatusText] = useState('');
  const indexingIntervalRef = useRef(null);
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
    return () => {
      if (indexingIntervalRef.current) {
        clearInterval(indexingIntervalRef.current);
      }
    };
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

    if (indexingIntervalRef.current) {
      clearInterval(indexingIntervalRef.current);
      indexingIntervalRef.current = null;
    }

    // 1. Upload start log & initial state
    console.log('[DocumentUpload] Upload started:', file.name, `(${file.size} bytes)`);
    setUploading(true);
    setUploadPhase('uploading');
    setUploadProgress(0);
    setUploadFileName(file.name);
    setUploadFileSize((file.size / (1024 * 1024)).toFixed(2) + ' MB');
    setUploadStatusText('Transmitting document bytes to server...');

    try {
      const res = await endpoints.uploadDocument(file, (progressEvent) => {
        if (progressEvent.phase === 'uploading') {
          // 2. Upload progress ticks: map 0-100% byte progress to 0-45% of the overall pipeline
          const mapped = Math.min(45, Math.round((progressEvent.percent / 100) * 45));
          setUploadProgress(mapped);
          setUploadStatusText(`Uploading bytes (${progressEvent.percent}%)...`);
          console.log('[DocumentUpload] Upload progress tick:', `${progressEvent.percent}% (mapped to ${mapped}%)`);
        } else if (progressEvent.phase === 'indexing') {
          // 3. Upload complete & 4. Indexing call start
          console.log('[DocumentUpload] Upload complete');
          console.log('[DocumentUpload] Indexing call start: extracting text chunks, calculating vector embeddings, indexing into MongoDB Atlas...');
          setUploadPhase('indexing');
          setUploadProgress((prev) => Math.max(prev, 50));
          setUploadStatusText('Extracting text chunks from PDF...');

          // Smooth simulated progress (50% -> 95%) with dynamic stage messages while awaiting backend response
          if (!indexingIntervalRef.current) {
            indexingIntervalRef.current = setInterval(() => {
              setUploadProgress((prev) => {
                if (prev < 68) {
                  setUploadStatusText('Chunking text & parsing semantic units...');
                  return prev + 3;
                } else if (prev < 84) {
                  setUploadStatusText('Generating dense vector embeddings in MongoDB Atlas...');
                  return prev + 2;
                } else if (prev < 95) {
                  setUploadStatusText('Finalizing vector search index & metadata...');
                  return prev + 1;
                }
                return prev;
              });
            }, 350);
          }
        }
      });

      // Clear simulated indexing interval
      if (indexingIntervalRef.current) {
        clearInterval(indexingIntervalRef.current);
        indexingIntervalRef.current = null;
      }

      // 5. Indexing resolve & 6. Final state update: snap to 100%
      console.log('[DocumentUpload] Indexing resolved:', res);
      console.log('[DocumentUpload] Final state update: 100% complete');

      setUploadPhase('complete');
      setUploadProgress(100);
      setUploadStatusText(`Indexed "${res.filename || file.name}" with ${res.total_chunks || 0} chunks!`);
      addToast(`Indexed "${res.filename || file.name}" with ${res.total_chunks || 0} chunks!`, 'success');

      // Refresh list
      loadDocuments();

      // Keep 100% visible for 2.5 seconds so user clearly sees full completion
      setTimeout(() => {
        setUploadPhase('idle');
        setUploading(false);
        setUploadProgress(0);
        setUploadFileName('');
      }, 2500);

    } catch (err) {
      if (indexingIntervalRef.current) {
        clearInterval(indexingIntervalRef.current);
        indexingIntervalRef.current = null;
      }
      console.log('[DocumentUpload] Indexing rejected:', err);
      console.error('Upload failed:', err);
      setUploadPhase('error');
      setUploadStatusText(`Upload failed: ${err.message}`);
      addToast(`Upload failed: ${err.message}`, 'error');

      setTimeout(() => {
        setUploading(false);
      }, 3500);
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
          {uploading
            ? uploadPhase === 'indexing'
              ? 'Extracting Chunks & Vector Indexing...'
              : 'Uploading Academic PDF...'
            : 'Upload Academic PDF'}
        </h3>
        <p style={{ fontSize: '0.92rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
          {uploading
            ? uploadStatusText
            : 'Drag and drop your lecture slides or syllabus PDF here, or click to browse (Max 25MB)'}
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
          {uploading
            ? uploadPhase === 'indexing'
              ? 'Vector Indexing...'
              : 'Uploading...'
            : 'Choose PDF File'}
        </button>
      </div>

      {/* Active Upload & Indexing Progress Card */}
      {uploadPhase !== 'idle' && (
        <div
          className="glass-card"
          style={{
            marginTop: '-18px',
            marginBottom: '36px',
            padding: '20px 24px',
            border: `1px solid ${
              uploadPhase === 'complete'
                ? 'rgba(16, 185, 129, 0.4)'
                : uploadPhase === 'error'
                ? 'rgba(239, 68, 68, 0.4)'
                : 'rgba(99, 102, 241, 0.4)'
            }`,
            borderRadius: 'var(--radius-lg)',
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            boxShadow:
              uploadPhase === 'complete'
                ? '0 0 20px rgba(16, 185, 129, 0.15)'
                : '0 0 20px rgba(99, 102, 241, 0.15)',
            textAlign: 'left',
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
                  width: '36px',
                  height: '36px',
                  borderRadius: 'var(--radius-sm)',
                  background:
                    uploadPhase === 'complete'
                      ? 'rgba(16, 185, 129, 0.2)'
                      : uploadPhase === 'error'
                      ? 'rgba(239, 68, 68, 0.2)'
                      : 'rgba(99, 102, 241, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color:
                    uploadPhase === 'complete'
                      ? 'var(--success)'
                      : uploadPhase === 'error'
                      ? 'var(--error)'
                      : 'var(--primary)',
                }}
              >
                {uploadPhase === 'complete' ? (
                  <CheckCircle2 size={20} />
                ) : uploadPhase === 'error' ? (
                  <AlertCircle size={20} />
                ) : (
                  <FileText size={20} />
                )}
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                  {uploadFileName || 'Document.pdf'}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {uploadFileSize && <span>{uploadFileSize} • </span>}
                  <span
                    style={{
                      color:
                        uploadPhase === 'complete'
                          ? 'var(--success)'
                          : uploadPhase === 'error'
                          ? 'var(--error)'
                          : 'var(--cyan)',
                    }}
                  >
                    {uploadPhase === 'uploading' && 'Phase 1/2: Uploading bytes'}
                    {uploadPhase === 'indexing' && 'Phase 2/2: Vector search indexing'}
                    {uploadPhase === 'complete' && 'Pipeline complete'}
                    {uploadPhase === 'error' && 'Error'}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <span
                style={{
                  fontSize: '1.2rem',
                  fontWeight: 700,
                  color:
                    uploadPhase === 'complete'
                      ? 'var(--success)'
                      : uploadPhase === 'error'
                      ? 'var(--error)'
                      : 'var(--primary)',
                }}
              >
                {Math.round(uploadProgress)}%
              </span>
            </div>
          </div>

          {/* Progress Track */}
          <div
            style={{
              width: '100%',
              height: '10px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              borderRadius: '999px',
              overflow: 'hidden',
              position: 'relative',
              marginBottom: '10px',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${uploadProgress}%`,
                transition: 'width 0.3s ease-in-out',
                borderRadius: '999px',
                background:
                  uploadPhase === 'complete'
                    ? 'linear-gradient(90deg, #10b981 0%, #059669 100%)'
                    : uploadPhase === 'error'
                    ? 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)'
                    : uploadPhase === 'indexing'
                    ? 'linear-gradient(90deg, #6366f1 0%, #06b6d4 50%, #8b5cf6 100%)'
                    : 'linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%)',
                boxShadow:
                  uploadPhase === 'complete'
                    ? '0 0 12px rgba(16, 185, 129, 0.6)'
                    : '0 0 12px rgba(99, 102, 241, 0.6)',
              }}
            />
          </div>

          {/* Status Footer */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.82rem',
              color: 'var(--text-muted)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {(uploadPhase === 'uploading' || uploadPhase === 'indexing') && (
                <Loader2 size={13} style={{ animation: 'spin 1.2s linear infinite' }} />
              )}
              <span>{uploadStatusText}</span>
            </div>
            {uploadPhase === 'complete' && (
              <span style={{ color: 'var(--success)', fontWeight: 600 }}>Ready for RAG</span>
            )}
          </div>
        </div>
      )}

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
