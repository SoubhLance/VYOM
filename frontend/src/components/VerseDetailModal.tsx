import React, { useEffect } from 'react';
import {
  X,
  Share2,
  BookOpen,
  Feather,
  RotateCcw,
} from 'lucide-react';
import type { GitaVerse } from '../data/gitaVerses';
import { useModalFocus } from '../utils/useModalFocus';
import { splitIastSpeaker, splitSanskritSpeaker } from '../utils/speaker';

/** The verse being shown: loading while its chapter files are fetched, error if they could not be */
export interface VerseView {
  id: string;
  status: 'loading' | 'ready' | 'error';
  verse: GitaVerse | null;
}

interface VerseDetailModalProps {
  view: VerseView | null;
  onClose: () => void;
  onRetry: (verseId: string) => void;
  onOpenQuoteCard: (verse: GitaVerse) => void;
}

/** Verses stored without line breaks (some glued speaker cases) get one line per danda */
const versesLines = (text: string) => (text.includes('\n') ? text : text.replace(/([।॥])\s*/gu, '$1\n').trim());

export const VerseDetailModal: React.FC<VerseDetailModalProps> = ({
  view,
  onClose,
  onRetry,
  onOpenQuoteCard,
}) => {
  const panelRef = useModalFocus<HTMLDivElement>(view !== null, onClose);
  // Both states below render backdrop > panel in the same position, so React keeps the same panel
  // node and useModalFocus's trap stays attached. When the content swaps, focus would fall to <body>.
  const status = view?.status;
  useEffect(() => {
    const panel = panelRef.current;
    if (status && status !== 'loading' && panel && !panel.contains(document.activeElement)) panel.focus();
  }, [status, panelRef]);
  if (!view) return null;
  const verse = view.verse;
  const sanskrit = splitSanskritSpeaker(verse?.sanskrit);
  const iast = splitIastSpeaker(verse?.transliteration);

  if (view.status !== 'ready' || !verse) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#4B3825]/45 animate-fade-in">
        <div ref={panelRef} role="dialog" aria-modal="true" aria-label={`Bhagavad Gita ${view.id}`} aria-busy={view.status === 'loading'} tabIndex={-1} className="relative w-full max-w-md filigree-card rounded-2xl p-6 shadow-2xl outline-none">
          <div className="flex items-start justify-between gap-3">
            <h2 className="font-cinzel text-lg font-bold text-[#2C261F]">Bhagavad Gita {view.id}</h2>
            <button onClick={onClose} aria-label="Close verse" className="p-2 -m-2 rounded-xl text-[#6A5A48] hover:text-[#2C261F] hover:bg-[#FFFDF8] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60">
              <X className="w-5 h-5" />
            </button>
          </div>
          {view.status === 'loading' ? (
            <p role="status" className="mt-4 font-cinzel text-xs tracking-wide text-[#6A5A48]">Opening the verse…</p>
          ) : (
            <div className="mt-4 space-y-3">
              <p role="alert" className="text-sm text-[#2C261F]">This verse couldn’t be loaded. Check your connection and try again.</p>
              <button onClick={() => onRetry(view.id)} className="inline-flex items-center gap-1.5 rounded-xl border border-[#C5A059]/45 bg-[#FFFDF8] px-3.5 py-2 text-xs font-semibold text-[#704B20] transition hover:border-[#A27427] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60">
                <RotateCcw className="h-3.5 w-3.5" /> Try again
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#4B3825]/45 animate-fade-in overflow-y-auto">
      <div ref={panelRef} role="dialog" aria-modal="true" aria-label={`Bhagavad Gita ${verse.verse_id}`} tabIndex={-1} className="relative w-full max-w-3xl my-8 filigree-card rounded-2xl overflow-hidden shadow-2xl p-6 md:p-8 flex flex-col max-h-[90vh] outline-none">
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
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close verse"
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

            <div className="my-4">
              {sanskrit.speaker && (
                <p lang="sa" className="font-sanskrit mb-1 text-sm text-[#704B20]">{sanskrit.speaker}</p>
              )}
              <p lang="sa" className="font-sanskrit text-2xl md:text-3xl leading-relaxed text-[#8C2D19] font-medium tracking-wide whitespace-pre-line">
                {versesLines(sanskrit.text)}
              </p>
            </div>

            {/* Transliteration */}
            <div className="pt-3 border-t border-[#C5A059]/15">
              {iast.speaker && <p className="iast mb-0.5 text-[11px] md:text-xs text-[#704B20]">{iast.speaker}</p>}
              <p className="iast text-xs md:text-sm leading-relaxed whitespace-pre-line">
                {iast.text}
              </p>
            </div>
          </div>

          {/* Word Meanings (Pada-Artha) */}
          {verse.word_meanings && <div className="p-4 rounded-xl bg-[#FFFDF8]/60 border border-[#C5A059]/15">
            <h4 className="font-cinzel text-xs font-bold text-[#C5A059] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Feather className="w-3.5 h-3.5 text-[#E28743]" /> Word-by-Word Essence (Pada-Vibhaga)
            </h4>
            <p className="font-sans-body text-xs md:text-sm text-[#6A5A48]/90 leading-relaxed">
              {verse.word_meanings}
            </p>
          </div>}

          {/* Translation */}
          {verse.translation && <div className="p-5 rounded-xl bg-gradient-to-r from-[#FFFDF8] to-[#F4ECE1] border-l-4 border-l-[#E28743] border-y border-r border-[#C5A059]/20 shadow-md">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-cinzel text-xs font-bold text-[#E28743] uppercase tracking-wider">
                English Translation
              </h4>
              <span className="font-cinzel text-[11px] text-[#6A5A48]/70 italic">
                By {verse.author}
              </span>
            </div>
            <p className="font-sans-body text-sm md:text-base text-[#2C261F] leading-relaxed italic">
              “{verse.translation}”
            </p>
          </div>}

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
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-[#FFFDF8] border border-[#C5A059]/20 text-[#6A5A48] hover:text-[#2C261F] font-cinzel text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
