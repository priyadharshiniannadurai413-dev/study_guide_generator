/**
 * src/components/DocumentSelector.jsx
 * Dropdown selector for picking between Global Syllabus and uploaded PDFs.
 */

import React, { useState, useEffect } from 'react';
import { FileText, BookMarked, RefreshCw } from 'lucide-react';
import { endpoints } from '../api/endpoints';

export function DocumentSelector({ selectedDocId, onSelectDocId, showLabel = true }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchDocs = async () => {
    try {
      setLoading(true);
      const docs = await endpoints.listDocuments();
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (err) {
      console.warn('Could not fetch user documents (auth or empty):', err);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {showLabel && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <label style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Knowledge Source:
          </label>
          <button
            type="button"
            onClick={fetchDocs}
            className="btn btn-ghost btn-sm"
            title="Refresh document list"
            style={{ padding: '2px 6px' }}
          >
            <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          </button>
        </div>
      )}

      <div style={{ position: 'relative' }}>
        <select
          value={selectedDocId || 'syllabus'}
          onChange={(e) => onSelectDocId(e.target.value)}
          className="select"
          style={{
            paddingLeft: '38px',
            fontSize: '0.9rem',
            cursor: 'pointer',
          }}
        >
          <option value="syllabus">📚 Global Syllabus & University Curriculum</option>
          {selectedDocId &&
            selectedDocId !== 'syllabus' &&
            !documents.some((d) => d.doc_id === selectedDocId) && (
              <option value={selectedDocId}>
                📄 Selected Document ({selectedDocId.slice(0, 8)}...)
              </option>
            )}
          {documents.map((doc) => (
            <option key={doc.doc_id} value={doc.doc_id}>
              📄 {doc.filename} ({doc.chunk_count} chunks)
            </option>
          ))}
        </select>

        <div
          style={{
            position: 'absolute',
            left: '12px',
            top: '50%',
            transform: 'translateY(-50%)',
            pointerEvents: 'none',
            color: 'var(--primary)',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {selectedDocId === 'syllabus' ? <BookMarked size={16} /> : <FileText size={16} />}
        </div>
      </div>
    </div>
  );
}
