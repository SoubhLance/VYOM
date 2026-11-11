import React from 'react';
import { X, Compass, BookOpen, Headphones, Cpu } from 'lucide-react';
import { VyomLogo } from './VyomLogo';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#4B3825]/35 backdrop-blur-md animate-fade-in overflow-y-auto">
      <div className="relative w-full max-w-2xl filigree-card rounded-2xl overflow-hidden p-6 md:p-8 shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#C5A059]/20">
          <div className="flex items-center gap-3">
            <VyomLogo size="sm" showSubtitle={false} />
            <div>
              <h3 className="font-cinzel text-base font-bold text-[#2C261F]">
                About VYOM Intelligence
              </h3>
              <p className="font-cinzel text-xs text-[#C5A059] italic">
                Ancient Wisdom. Infinite Understanding.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#6A5A48]/70 hover:text-[#2C261F] hover:bg-[#FFFDF8] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto my-4 pr-1 space-y-4 text-xs md:text-sm text-[#6A5A48] leading-relaxed">
          <div className="p-4 rounded-xl bg-[#FFFDF8]/70 border border-[#C5A059]/20 space-y-2">
            <h4 className="font-cinzel text-xs font-bold text-[#E28743] uppercase tracking-wider flex items-center gap-2">
              <Compass className="w-4 h-4" /> Gateway &amp; Sanctuary
            </h4>
            <p>
              A short film of the Kurukshetra field opens VYOM, then fades into a quiet cream-and-gold sanctuary where you can ask a question, open the five Gita pillars, or begin reading.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#FFFDF8]/70 border border-[#C5A059]/20 space-y-2">
            <h4 className="font-cinzel text-xs font-bold text-[#E28743] uppercase tracking-wider flex items-center gap-2">
              <BookOpen className="w-4 h-4" /> The Sacred Book
            </h4>
            <p>
              All 701 verses, chapter by chapter, in Devanagari with transliteration and English from five translators: Swami Sivananda, Swami Gambirananda, Swami Adidevananda, Dr. S. Sankaranarayan and Shri Purohit Swami. Any verse can be shared as a quote card.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#FFFDF8]/70 border border-[#C5A059]/20 space-y-2">
            <h4 className="font-cinzel text-xs font-bold text-[#E28743] uppercase tracking-wider flex items-center gap-2">
              <Headphones className="w-4 h-4" /> Recitation
            </h4>
            <p>
              Each shloka has a real recited clip, cut from a full chanting of the Gita. Where the reciter joins lines across two verses, the clip is marked as shared with its neighbour.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#FFFDF8]/70 border border-[#C5A059]/20 space-y-2">
            <h4 className="font-cinzel text-xs font-bold text-[#E28743] uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4" /> Grounded Answers
            </h4>
            <p>
              Answers are drawn only from the verses VYOM retrieves, along with the verses that follow them in the dialogue and classical commentaries such as Sri Shankaracharya, Sri Ramanujacharya and Swami Chinmayananda. Quotes are checked against the source text, and any sentence that cannot be supported is removed.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-[#C5A059]/20 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-[#E28743] to-[#C5A059] text-[#F4ECE1] font-cinzel text-xs font-bold shadow-md hover:brightness-110"
          >
            Return to the sanctuary
          </button>
        </div>
      </div>
    </div>
  );
};
