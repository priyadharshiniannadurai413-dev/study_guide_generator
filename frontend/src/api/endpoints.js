/**
 * src/api/endpoints.js
 * High-level API endpoints communicating with FastAPI backend.
 */

import { apiRequest, getEffectiveToken, API_BASE } from './client';

export const endpoints = {
  // Health check
  async getHealth() {
    return await apiRequest('/health');
  },

  // Document Management
  async listDocuments() {
    return await apiRequest('/api/documents');
  },

  async uploadDocument(file, onProgress) {
    const token = await getEffectiveToken();
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);

      xhr.open('POST', `${API_BASE}/api/documents/upload`);

      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      if (xhr.upload && onProgress) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable && e.total > 0) {
            const percent = Math.round((e.loaded / e.total) * 100);
            onProgress({ phase: 'uploading', loaded: e.loaded, total: e.total, percent });
          }
        });

        xhr.upload.addEventListener('load', () => {
          onProgress({ phase: 'indexing', percent: 100 });
        });
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const res = JSON.parse(xhr.responseText);
            resolve(res);
          } catch {
            resolve(xhr.responseText);
          }
        } else {
          let errorDetail = `Upload failed with status ${xhr.status}`;
          try {
            const res = JSON.parse(xhr.responseText);
            errorDetail = res.detail || res.error || errorDetail;
          } catch {
            if (xhr.responseText) errorDetail = xhr.responseText;
          }
          reject(new Error(errorDetail));
        }
      };

      xhr.onerror = () => {
        reject(new Error('Network error during file upload'));
      };

      xhr.ontimeout = () => {
        reject(new Error('Upload request timed out'));
      };

      xhr.send(formData);
    });
  },

  async deleteDocument(docId) {
    return await apiRequest(`/api/documents/${encodeURIComponent(docId)}`, {
      method: 'DELETE',
    });
  },

  // Dedicated Study Generation
  async generateStudyNotes({ docId, url, topic, difficulty = 'intermediate', enableWeb = false }) {
    return await apiRequest('/api/study/notes', {
      method: 'POST',
      body: JSON.stringify({
        doc_id: docId || (url ? null : 'syllabus'),
        url: url || null,
        topic: topic || null,
        difficulty,
        enable_web: Boolean(enableWeb),
      }),
    });
  },

  async generateMCQs({ docId, url, count = 20, topic, difficulty = 'intermediate', enableWeb = false }) {
    return await apiRequest('/api/study/mcq', {
      method: 'POST',
      body: JSON.stringify({
        doc_id: docId || (url ? null : 'syllabus'),
        url: url || null,
        count: parseInt(count, 10),
        topic: topic || null,
        difficulty,
        enable_web: Boolean(enableWeb || url),
      }),
    });
  },

  async exportPDF({ notes, topic, docId, difficulty = 'intermediate' }) {
    return await apiRequest('/api/study/export/pdf', {
      method: 'POST',
      body: JSON.stringify({
        notes: notes || null,
        topic: topic || null,
        doc_id: docId || null,
        difficulty,
      }),
    });
  },

  async exportDOCX({ notes, topic, docId, difficulty = 'intermediate' }) {
    return await apiRequest('/api/study/export/docx', {
      method: 'POST',
      body: JSON.stringify({
        notes: notes || null,
        topic: topic || null,
        doc_id: docId || null,
        difficulty,
      }),
    });
  },

  // 2-Mark Conceptual Test & Semantic Evaluation
  async generateTwoMarkTest({ docId, pastedText, count = 5 }) {
    return await apiRequest('/api/study/generate-test', {
      method: 'POST',
      body: JSON.stringify({
        doc_id: docId || null,
        pasted_text: pastedText || null,
        question_count: parseInt(count, 10),
      }),
    });
  },

  async evaluateAnswer({ questionId, question, modelAnswer, keyPoints, studentAnswer }) {
    return await apiRequest('/api/study/evaluate-answer', {
      method: 'POST',
      body: JSON.stringify({
        question_id: questionId,
        question,
        model_answer: modelAnswer,
        key_points: keyPoints,
        student_answer: studentAnswer,
      }),
    });
  },

  // Voice Processing
  async transcribeAudio(audioBlob, filename = 'audio.wav') {
    const formData = new FormData();
    formData.append('file', audioBlob, filename);
    return await apiRequest('/api/voice/transcribe', {
      method: 'POST',
      body: formData,
      isFormData: true,
    });
  },

  async synthesizeSpeech({ text, voice }) {
    return await apiRequest('/api/voice/synthesize', {
      method: 'POST',
      body: JSON.stringify({
        text,
        voice: voice || undefined,
      }),
    });
  },

  // GitHub MCP Integration
  async getGitHubStatus() {
    return await apiRequest('/api/auth/github/status');
  },

  async getGitHubAuthUrl(customRedirectUri) {
    const redirectParam = customRedirectUri
      ? `&redirect_uri=${encodeURIComponent(customRedirectUri)}`
      : '';
    return await apiRequest(`/api/auth/github/login?redirect=false${redirectParam}`);
  },

  async postGitHubCallback({ code, state }) {
    return await apiRequest('/api/auth/github/callback', {
      method: 'POST',
      body: JSON.stringify({ code, state }),
    });
  },

  async disconnectGitHub() {
    return await apiRequest('/api/auth/github/disconnect', {
      method: 'POST',
    });
  },

  // Web Research & Extraction (Fetch MCP)
  async fetchWebDocument(url) {
    return await apiRequest('/api/web/fetch', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  },

  async askWebQuestion({ url, question }) {
    return await apiRequest('/api/web/ask', {
      method: 'POST',
      body: JSON.stringify({ url, question }),
    });
  },

  async generateWebStudyNotes({ url, topic, difficulty = 'intermediate' }) {
    return await apiRequest('/api/web/notes', {
      method: 'POST',
      body: JSON.stringify({ url, topic: topic || null, difficulty }),
    });
  },
};

