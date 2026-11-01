import React from 'react';
import type { Clip } from '../services/api';
import { SanskritAudio } from '../services/audioChant';
import { onClipPlayStart, onClipPlayEndOrPause } from '../services/audioCoordinator';
import { Volume2, Info } from 'lucide-react';

interface ClipPlayerProps {
  clips?: Clip[];
}

export const ClipPlayer: React.FC<ClipPlayerProps> = ({ clips }) => {
  if (!clips || clips.length === 0) {
    return null;
  }

  const handlePlay = (e: React.SyntheticEvent<HTMLAudioElement>) => {
    SanskritAudio.stop();
    onClipPlayStart(e.currentTarget);
  };

  const handlePauseOrEnd = (e: React.SyntheticEvent<HTMLAudioElement>) => {
    onClipPlayEndOrPause(e.currentTarget);
  };

  return (
    <div className="space-y-3 mt-2">
      {clips.map((clip, idx) => (
        <div
          key={clip.clip_id || idx}
          className="rounded-xl border border-[#C5A059]/30 bg-[#FAF6EB]/80 p-3 shadow-sm space-y-2 transition-all hover:border-[#C5A059]/50"
        >
          {/* Header / Recitation Label */}
          <div className="flex items-center justify-between text-xs">
            <span className="font-cinzel font-semibold text-[#8C2D19] flex items-center gap-1.5">
              <Volume2 className="w-3.5 h-3.5 text-[#E28743]" />
              {clips.length > 1 ? `Recitation ${idx + 1} of ${clips.length}` : 'Vedic Recitation'}
            </span>
            {clip.partial && (
              <span className="text-[10px] font-cinzel text-[#A27427] bg-[#F1E0BB]/60 px-2 py-0.5 rounded-full border border-[#C5A059]/30">
                Shared Shloka
              </span>
            )}
          </div>

          {/* HTML5 Audio Player */}
          <audio
            controls
            preload="none"
            src={clip.audio_url}
            onPlay={handlePlay}
            onPause={handlePauseOrEnd}
            onEnded={handlePauseOrEnd}
            className="w-full h-8 rounded"
          />

          {/* Spoken Lines Caption in Devanagari */}
          {clip.spoken_lines && clip.spoken_lines.length > 0 && (
            <div
              className="font-sanskrit text-xs text-[#2C261F]/90 leading-relaxed bg-[#FFFDF8]/70 p-2 rounded-lg border border-[#C5A059]/20"
              lang="sa"
            >
              {clip.spoken_lines.map((line, lIdx) => (
                <p key={lIdx}>{line}</p>
              ))}
            </div>
          )}

          {/* Partial Recording Note */}
          {clip.partial && (
            <p className="text-[10px] text-[#A27427] italic font-cinzel flex items-center gap-1">
              <Info className="w-3 h-3 text-[#A27427] shrink-0" />
              This recording covers lines shared with a neighbouring verse
            </p>
          )}
        </div>
      ))}
    </div>
  );
};

