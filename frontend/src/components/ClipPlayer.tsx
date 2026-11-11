import React, { useEffect, useRef, useState } from 'react';
import type { Clip } from '../services/api';
import { onClipPlayStart, onClipPlayEndOrPause } from '../services/audioCoordinator';
import { Info, Pause, Play, Volume2 } from 'lucide-react';

interface ClipPlayerProps {
  clips?: Clip[];
}

const formatTime = (seconds: number) => {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

/**
 * Recitation player for a verse: one "Play verse" button (Sacred Book style).
 * Partial clips play one after another. All playback goes through audioCoordinator.
 */
export const ClipPlayer: React.FC<ClipPlayerProps> = ({ clips }) => {
  const audioRefs = useRef<(HTMLAudioElement | null)[]>([]);
  const [playingIdx, setPlayingIdx] = useState<number | null>(null);
  const [durations, setDurations] = useState<number[]>([]);

  // Pause on unmount so a removed card never keeps playing
  useEffect(() => {
    const els = audioRefs.current;
    return () => {
      els.forEach((el) => {
        if (el && !el.paused) {
          el.pause();
          onClipPlayEndOrPause(el);
        }
      });
    };
  }, []);

  if (!clips || clips.length === 0) {
    return null;
  }

  const knownDurations = durations.filter((d) => Number.isFinite(d) && d > 0);
  const totalDuration = knownDurations.length === clips.length ? knownDurations.reduce((a, b) => a + b, 0) : null;
  const isPlaying = playingIdx !== null;
  const hasPartial = clips.some((c) => c.partial);

  const playFrom = (idx: number) => {
    const el = audioRefs.current[idx];
    if (!el) return;
    el.currentTime = 0;
    el.play().catch(() => {
      setPlayingIdx(null);
      onClipPlayEndOrPause(el);
    });
  };

  const handleToggle = () => {
    if (playingIdx !== null) {
      audioRefs.current[playingIdx]?.pause();
      return;
    }
    playFrom(0);
  };

  return (
    <div className="mt-2 space-y-2 rounded-xl border border-[#C5A059]/30 bg-[#FAF6EB]/80 p-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-cinzel text-xs font-semibold text-[#8C2D19] flex items-center gap-1.5">
          <Volume2 className="w-3.5 h-3.5 text-[#E28743]" />
          Sacred recitation
          {totalDuration !== null && (
            <span className="font-sans-body text-[10px] font-normal text-[#6A5A48]">· {formatTime(totalDuration)}</span>
          )}
        </span>
        <button
          type="button"
          onClick={handleToggle}
          className="vyom-play-button"
          aria-label={isPlaying ? 'Pause recitation' : 'Play recitation'}
        >
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          {isPlaying ? 'Pause' : 'Play verse'}
        </button>
      </div>

      {clips.map((clip, idx) => (
        <audio
          key={clip.clip_id || idx}
          ref={(el) => {
            audioRefs.current[idx] = el;
          }}
          src={clip.audio_url}
          preload="metadata"
          className="hidden"
          onLoadedMetadata={(e) => {
            const d = e.currentTarget.duration;
            setDurations((prev) => {
              const next = [...prev];
              next[idx] = d;
              return next;
            });
          }}
          onPlay={(e) => {
            setPlayingIdx(idx);
            onClipPlayStart(e.currentTarget);
          }}
          onPause={(e) => {
            setPlayingIdx((cur) => (cur === idx ? null : cur));
            onClipPlayEndOrPause(e.currentTarget);
          }}
          onEnded={(e) => {
            onClipPlayEndOrPause(e.currentTarget);
            if (idx + 1 < clips.length) {
              playFrom(idx + 1);
            } else {
              setPlayingIdx(null);
            }
          }}
          onError={(e) => {
            setPlayingIdx((cur) => (cur === idx ? null : cur));
            onClipPlayEndOrPause(e.currentTarget);
          }}
        />
      ))}

      {/* Spoken lines in Devanagari, per clip */}
      {clips.map((clip, idx) =>
        clip.spoken_lines && clip.spoken_lines.length > 0 ? (
          <div
            key={`lines-${clip.clip_id || idx}`}
            className={`font-sanskrit text-xs text-[#2C261F]/90 leading-relaxed p-2 rounded-lg border transition-colors ${
              playingIdx === idx ? 'bg-[#FFFDF8] border-[#C5A059]/50' : 'bg-[#FFFDF8]/70 border-[#C5A059]/20'
            }`}
            lang="sa"
          >
            {clip.spoken_lines.map((line, lIdx) => (
              <p key={lIdx}>{line}</p>
            ))}
          </div>
        ) : null,
      )}

      {hasPartial && (
        <p className="text-[10px] text-[#A27427] italic font-cinzel flex items-center gap-1">
          <Info className="w-3 h-3 text-[#A27427] shrink-0" />
          This recording covers lines shared with a neighbouring verse
        </p>
      )}
    </div>
  );
};
