/**
 * src/components/VoiceRecorder.jsx
 * Microphone voice recorder using MediaRecorder and Groq Whisper API.
 */

import React, { useState, useRef } from 'react';
import { Mic, Square, Loader2, AlertCircle } from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { useToast } from '../context/ToastContext';

export function VoiceRecorder({ onTranscriptionComplete, isCompact = false }) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [recordTime, setRecordTime] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const { addToast } = useToast();

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      // Determine supported mimeType
      let mimeType = 'audio/webm';
      if (!MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/mp4';
      }

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop audio tracks
        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        if (audioBlob.size === 0) {
          addToast('No audio detected.', 'warning');
          return;
        }

        try {
          setTranscribing(true);
          const extension = mimeType.includes('webm') ? 'webm' : 'mp4';
          const res = await endpoints.transcribeAudio(audioBlob, `audio_prompt.${extension}`);
          if (res?.text) {
            onTranscriptionComplete(res.text);
            addToast('Voice transcribed successfully!', 'success');
          } else {
            addToast('No speech recognized.', 'info');
          }
        } catch (err) {
          console.error('Transcription error:', err);
          addToast(`Voice transcription failed: ${err.message}`, 'error');
        } finally {
          setTranscribing(false);
        }
      };

      mediaRecorder.start(250);
      setRecording(true);
      setRecordTime(0);

      timerRef.current = setInterval(() => {
        setRecordTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Microphone permission error:', err);
      addToast('Microphone access denied or not found.', 'error');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  if (transcribing) {
    return (
      <div
        className="badge badge-primary"
        style={{
          padding: isCompact ? '6px 10px' : '8px 14px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
        <span>Transcribing audio...</span>
      </div>
    );
  }

  if (recording) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
        <div
          className="badge"
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#f87171',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#ef4444',
              display: 'inline-block',
              animation: 'pulse 1s infinite',
            }}
          />
          <span>Recording: {formatTime(recordTime)}</span>
        </div>

        <button
          onClick={stopRecording}
          type="button"
          className="btn btn-danger btn-sm"
          title="Stop Recording"
          style={{ padding: '6px 12px', borderRadius: 'var(--radius-full)' }}
        >
          <Square size={13} fill="#ffffff" />
          <span>Stop</span>
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={startRecording}
      type="button"
      className={isCompact ? 'btn btn-secondary btn-icon' : 'btn btn-secondary btn-sm'}
      title="Speak to Ask (Voice Input)"
      style={{
        borderRadius: 'var(--radius-full)',
        borderColor: 'var(--border-light)',
      }}
    >
      <Mic size={16} color="var(--primary)" />
      {!isCompact && <span>Voice Input</span>}
    </button>
  );
}
