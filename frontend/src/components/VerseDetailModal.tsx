import React, { useState, useEffect } from 'react';
import {
  X,
  Volume2,
  VolumeX,
  Sparkles,
  Share2,
  BookOpen,
  Feather,
} from 'lucide-react';
import type { GitaVerse } from '../data/gitaVerses';
import { SanskritAudio } from '../services/audioChant';

interface VerseDetailModalProps {
  verse: GitaVerse | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenQuoteCard: (verse: GitaVerse) => void;
}

export const VerseDetailModal: React.FC<VerseDetailModalProps> = ({
  verse,
  isOpen,
  onClose,
  onOpenQuoteCard,
}) => {
  const [isPlayingChant, setIsPlayingChant] = useState(false);

  useEffect(() => {
    // If modal closes, don't necessarily stop audio unless user wants
    return () => {
      // cleanups
    };
  }, []);

  if (!isOpen || !verse) return null;

  const handleToggleChant = () => {
    if (isPlayingChant) {
      SanskritAudio.stop();
      setIsPlayingChant(false);
    } else {
      setIsPlayingChant(true);
      SanskritAudio.playShlokaChant(
        verse.sanskrit,
        verse.transliteration,
        () => setIsPlayingChant(false)
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#4B3825]/35 backdrop-blur-md animate-fade-in overflow-y-auto">
      <div className="relative w-full max-w-3xl my-8 filigree-card rounded-2xl overflow-hidden shadow-2xl p-6 md:p-8 flex flex-col max-h-[90vh]">
        {/* Header Bar */}
        <div className="flex items-center justify-between pb-4 border-b border-[#C5A059]/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-[#F4ECE1] border border-[#C5A059]/30 text-[#E28743]">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-cinzel text-lg md:text-xl font-bold text-[#2C261F]">
                  Srimad Bhagavad Gita {verse.verse_id}
                </h2>
                <span className="px-2.5 py-0.5 rounded-full bg-[#C5A059]/15 border border-[#C5A059]/30 text-[#C5A059] font-cinzel text-[11px] font-semibold">
                  Chapter {verse.chapter}, Shloka {verse.verse}
                </span>
              </div>
              <p className="font-cinzel text-xs text-[#6A5A48]/70 italic mt-0.5">
                {verse.theme}
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              if (isPlayingChant) SanskritAudio.stop();
              onClose();
            }}
            className="p-2 rounded-xl text-[#6A5A48]/70 hover:text-[#2C261F] hover:bg-[#FFFDF8] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="overflow-y-auto pr-2 my-4 space-y-6">
          {/* Sanskrit Devanagari Box */}
          <div className="relative p-6 rounded-xl bg-gradient-to-br from-[#FFFDF8] to-[#F4ECE1] border border-[#C5A059]/30 text-center shadow-inner">
            <span className="absolute top-2.5 left-3 font-cinzel text-[10px] text-[#C5A059]/60 uppercase tracking-widest">
              Original Sanskrit
            </span>

            {/* Chanting Action Button */}
            <div className="absolute top-2.5 right-3">
              <button
                onClick={handleToggleChant}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-cinzel font-semibold transition-all ${
                  isPlayingChant
                    ? 'bg-[#E28743] text-[#F4ECE1] shadow-[0_0_15px_rgba(255,183,3,0.4)]'
                    : 'bg-[#F4ECE1] border border-[#C5A059]/30 text-[#2C261F] hover:border-[#E28743]/50'
                }`}
              >
                {isPlayingChant ? (
                  <>
                    <Volume2 className="w-3.5 h-3.5 animate-pulse text-[#F4ECE1]" />
                    <span>Chanting Active...</span>
                  </>
                ) : (
                  <>
                    <VolumeX className="w-3.5 h-3.5 text-[#C5A059]" />
                    <span>Listen Vedic Chant</span>
                  </>
                )}
              </button>
            </div>

            <div className="my-4">
              <p className="font-sanskrit text-2xl md:text-3xl leading-relaxed text-[#FFF8E7] font-medium tracking-wide drop-shadow-sm whitespace-pre-line">
                {verse.sanskrit}
              </p>
            </div>

            {/* Transliteration */}
            <div className="pt-3 border-t border-[#C5A059]/15">
              <p className="font-cinzel text-xs md:text-sm text-[#C5A059] italic tracking-wide whitespace-pre-line">
                {verse.transliteration}
              </p>
            </div>
          </div>

          {/* Word Meanings (Pada-Artha) */}
          <div className="p-4 rounded-xl bg-[#FFFDF8]/60 border border-[#C5A059]/15">
            <h4 className="font-cinzel text-xs font-bold text-[#C5A059] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Feather className="w-3.5 h-3.5 text-[#E28743]" /> Word-by-Word Essence (Pada-Vibhaga)
            </h4>
            <p className="font-sans-body text-xs md:text-sm text-[#6A5A48]/90 leading-relaxed">
              {verse.word_meanings}
            </p>
          </div>

          {/* Translation */}
          <div className="p-5 rounded-xl bg-gradient-to-r from-[#FFFDF8] to-[#F4ECE1] border-l-4 border-l-[#E28743] border-y border-r border-[#C5A059]/20 shadow-md">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-cinzel text-xs font-bold text-[#E28743] uppercase tracking-wider">
                Authoritative English Translation
              </h4>
              <span className="font-cinzel text-[11px] text-[#6A5A48]/70 italic">
                By {verse.author}
              </span>
            </div>
            <p className="font-sans-body text-sm md:text-base text-[#2C261F] leading-relaxed italic">
              “{verse.translation}”
            </p>
          </div>

          {/* Philosophical Commentary */}
          <div className="p-5 rounded-xl bg-[#FFFDF8]/60 border border-[#C5A059]/15">
            <h4 className="font-cinzel text-xs font-bold text-[#C5A059] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#E28743]" /> Vedantic Commentary & Context
            </h4>
            <p className="font-sans-body text-xs md:text-sm text-[#6A5A48] leading-relaxed">
              {verse.commentary_summary}
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-4 border-t border-[#C5A059]/20 flex items-center justify-between">
          <button
            onClick={() => onOpenQuoteCard(verse)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#E28743]/20 to-[#C5A059]/20 border border-[#C5A059]/40 text-[#2C261F] hover:border-[#E28743] hover:text-[#2C261F] transition-all font-cinzel text-xs font-semibold shadow-sm"
          >
            <Share2 className="w-4 h-4 text-[#E28743]" />
            Generate Royal Quote Card
          </button>

          <button
            onClick={() => {
              if (isPlayingChant) SanskritAudio.stop();
              onClose();
            }}
            className="px-5 py-2.5 rounded-xl bg-[#FFFDF8] border border-[#C5A059]/20 text-[#6A5A48] hover:text-[#2C261F] font-cinzel text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
