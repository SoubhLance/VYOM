import React from 'react';
import { X, Sparkles, Compass, Cpu } from 'lucide-react';
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
              <Compass className="w-4 h-4" /> 3D Kurukshetra Diorama (Rathachakra-Dhari)
            </h4>
            <p>
              Showcasing the turning point of the Mahabharata: Lord Sri Krishna leaping forward from the golden royal chariot, clutching aloft the spiked chariot wheel in place of His Sudarshana Chakra, as Partha (Arjuna) clings to His lotus feet in total surrender, begging Him not to break His vow of non-combat.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#FFFDF8]/70 border border-[#C5A059]/20 space-y-2">
            <h4 className="font-cinzel text-xs font-bold text-[#E28743] uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4" /> Multimodal Architecture & RAG Pipeline
            </h4>
            <p>
              VYOM indexes the complete corpus of 701 Sanskrit verses, including transliterations, word-by-word meanings, and authoritative commentaries from Adi Shankaracharya, Sri Ramanuja, and Swami Chinmayananda. Dense retrieval powers context grounding with conversational neighbor expansion (+1, +2 verses) to guarantee dialogue coherence.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#FFFDF8]/70 border border-[#C5A059]/20 space-y-2">
            <h4 className="font-cinzel text-xs font-bold text-[#E28743] uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> Sanskrit Audio Synthesis & Quote Studio
            </h4>
            <p>
              Integrated Web Audio API Tanpura drone (Sa-Pa harmonic frequencies) and classical Vedic Anushtup meter recitation player, paired with an instant canvas-rendered quote card generator for sharing timeless insights.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-[#C5A059]/20 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-[#E28743] to-[#C5A059] text-[#F4ECE1] font-cinzel text-xs font-bold shadow-md hover:brightness-110"
          >
            Enter Kurukshetra
          </button>
        </div>
      </div>
    </div>
  );
};
