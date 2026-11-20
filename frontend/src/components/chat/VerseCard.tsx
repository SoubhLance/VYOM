import { ArrowUpRight, Share2 } from 'lucide-react';
import { normalizeVerseId } from '../../data/verseStore';
import type { Source } from '../../services/api';
import { splitIastSpeaker, splitSanskritSpeaker } from '../../utils/speaker';
import { ClipPlayer } from '../ClipPlayer';
import { VerseCardTranslation } from './VerseCardTranslation';

interface VerseCardProps {
  source: Source;
  /** data-verse-card value, so a citation chip can find and highlight this card */
  cardKey: string;
  highlighted: boolean;
  onOpenVerseDetail: (verseId: string) => void;
  onOpenQuoteCard: (verseId: string) => void;
}

/** One verse under an answer: Sanskrit, IAST, the prompt's English translation and a compact player. */
export function VerseCard({ source: s, cardKey, highlighted, onOpenVerseDetail, onOpenQuoteCard }: VerseCardProps) {
  const verseId = normalizeVerseId(s.verse_id);
  const sanskritParts = splitSanskritSpeaker(s.sanskrit);
  const iastParts = splitIastSpeaker(s.transliteration);

  return (
    <div
      data-verse-card={cardKey}
      tabIndex={-1}
      className={`space-y-2 rounded-xl border border-[#C5A059]/30 bg-[#FFFDF8]/90 p-3 shadow-sm outline-none transition-colors hover:border-[#C5A059]/60 ${highlighted ? 'verse-highlight' : ''}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="rounded-md border border-[#C5A059]/30 bg-[#F1E0BB]/60 px-2 py-0.5 font-cinzel text-xs font-bold text-[#8C2D19]">
            BG {s.verse_id}
          </span>
          {s.is_neighbor && s.neighbor_of && (
            <span className="font-cinzel text-[10px] italic text-[#6A5A48]">(Context for BG {s.neighbor_of})</span>
          )}
        </div>
        {verseId && (
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onOpenVerseDetail(verseId)}
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-cinzel text-[11px] font-semibold text-[#8C2D19] transition-colors hover:text-[#2C261F] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
              title="View full verse details"
            >
              <span>Exposition</span>
              <ArrowUpRight className="h-3 w-3 opacity-70" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => onOpenQuoteCard(verseId)}
              aria-label={`Quote card for BG ${verseId}`}
              title="Make a quote card"
              className="rounded-md p-1 text-[#A27427] transition-colors hover:bg-[#F4ECE1] hover:text-[#2C261F] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
            >
              <Share2 className="h-3 w-3" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      {sanskritParts.text && (
        <div lang="sa">
          {sanskritParts.speaker && <p className="font-sanskrit text-[11px] text-[#704B20]">{sanskritParts.speaker}</p>}
          <p className="font-sanskrit text-xs leading-relaxed text-[#2C261F]">{sanskritParts.text}</p>
        </div>
      )}

      {iastParts.text && (
        <div>
          {iastParts.speaker && <p className="iast text-[11px] text-[#704B20]">{iastParts.speaker}</p>}
          <p className="iast text-xs leading-relaxed">{iastParts.text}</p>
        </div>
      )}

      <VerseCardTranslation verseId={s.verse_id} />

      {/* Compact: the card already shows the verse, so the player doesn't repeat it */}
      {s.clips && s.clips.length > 0 && <ClipPlayer clips={s.clips} compact />}
    </div>
  );
}
