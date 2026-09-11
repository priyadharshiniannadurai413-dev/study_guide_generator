/**
 * src/api/endpoints.js
 * High-level API endpoints communicating with FastAPI backend.
 */

import { apiRequest } from './client';

export const endpoints = {
  // Health check
  async getHealth() {
    return await apiRequest('/health');
  },

  // Document Management
  async listDocuments() {
    return await apiRequest('/api/documents');
  },

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    return await apiRequest('/api/documents/upload', {
      method: 'POST',
      body: formData,
      isFormData: true,
    });
  },

  async deleteDocument(docId) {
    return await apiRequest(`/api/documents/${encodeURIComponent(docId)}`, {
      method: 'DELETE',
    });
  },

  // Dedicated Study Generation
  async generateStudyNotes({ docId, topic }) {
    return await apiRequest('/api/study/notes', {
      method: 'POST',
      body: JSON.stringify({
        doc_id: docId,
        topic: topic || null,
      }),
    });
  },

  async generateMCQs({ docId, count = 5, topic }) {
    return await apiRequest('/api/study/mcq', {
      method: 'POST',
      body: JSON.stringify({
        doc_id: docId,
        count: parseInt(count, 10),
        topic: topic || null,
      }),
    });
  },

  async exportPDF({ notes, topic, docId }) {
    return await apiRequest('/api/study/export/pdf', {
      method: 'POST',
      body: JSON.stringify({
        notes: notes || null,
        topic: topic || null,
        doc_id: docId || null,
      }),
    });
  },

  async exportDOCX({ notes, topic, docId }) {
    return await apiRequest('/api/study/export/docx', {
      method: 'POST',
      body: JSON.stringify({
        notes: notes || null,
        topic: topic || null,
        doc_id: docId || null,
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
};
