/**
 * src/components/AudioPlayer.jsx
 * Audio speech synthesizer & player with visual wave bars.
 */

import React, { useState, useRef } from 'react';
import { Volume2, VolumeX, Loader2, Play, Pause } from 'lucide-react';
import { endpoints } from '../api/endpoints';
import { useToast } from '../context/ToastContext';

export function AudioPlayer({ text, voice = 'en-US-JennyNeural', buttonStyle = {} }) {
  const [loading, setLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);
  const audioUrlRef = useRef(null);
  const { addToast } = useToast();

  const handlePlayVoice = async () => {
    if (!text || !text.trim()) {
      addToast('No text available to synthesize.', 'warning');
      return;
    }

    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    // If audio already generated and loaded, replay
    if (audioRef.current && audioUrlRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play();
      setIsPlaying(true);
      return;
    }

    try {
      setLoading(true);
      const audioBlob = await endpoints.synthesizeSpeech({ text: text.trim(), voice });
      const blobUrl = URL.createObjectURL(audioBlob);
      audioUrlRef.current = blobUrl;

      const audio = new Audio(blobUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setIsPlaying(false);
      };

      audio.onerror = (e) => {
        console.error('Audio playback error:', e);
        setIsPlaying(false);
        addToast('Audio playback failed.', 'error');
      };

      await audio.play();
      setIsPlaying(true);
    } catch (err) {
      console.error('Failed to synthesize speech:', err);
      addToast(`Speech synthesis failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', ...buttonStyle }}>
      <button
        onClick={handlePlayVoice}
        disabled={loading}
        className="btn btn-secondary btn-sm"
        title={isPlaying ? 'Pause Voice' : 'Read Out Loud (Edge-TTS)'}
        style={{
          padding: '6px 12px',
          borderRadius: 'var(--radius-full)',
          background: isPlaying ? 'rgba(6, 182, 212, 0.18)' : 'rgba(255, 255, 255, 0.06)',
          borderColor: isPlaying ? 'var(--cyan)' : 'var(--border-subtle)',
          color: isPlaying ? 'var(--cyan)' : 'var(--text-secondary)',
        }}
      >
        {loading ? (
          <Loader2 size={14} className="shimmer" style={{ animation: 'spin 1s linear infinite' }} />
        ) : isPlaying ? (
          <Pause size={14} />
        ) : (
          <Volume2 size={14} />
        )}
        <span style={{ fontSize: '0.8rem' }}>{isPlaying ? 'Playing...' : 'Listen'}</span>
      </button>

      {isPlaying && (
        <div className="wave-bars" title="Synthesized Speech Streaming">
          <div className="wave-bar" />
          <div className="wave-bar" />
          <div className="wave-bar" />
          <div className="wave-bar" />
          <div className="wave-bar" />
        </div>
      )}
    </div>
  );
}
