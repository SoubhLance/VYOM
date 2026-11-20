import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, BookOpen, ChevronDown, Info, Share2 } from 'lucide-react';
import { normalizeVerseId } from '../../data/verseStore';
import type { Source } from '../../services/api';
import type { ChatMessage } from '../ChatPanel';
import { SuggestionChips } from '../SuggestedChips';
import { AnswerMarkdown, type TextRenderer } from './AnswerMarkdown';
import { VerseCard } from './VerseCard';

/** "(BG 2.47)" or "BG 2.47" in answer text */
const CITATION = /\(?\bBG\s*(\d{1,2})[.:](\d{1,3})\)?/g;
const NEARBY_LIMIT = 3;
const HIGHLIGHT_MS = 1200;
const REMOVED_STATEMENT = 'One unsupported statement was removed from the answer.';

/** Verse ids cited in a piece of answer text, in order of first appearance */
function citedVerseIds(text: string): string[] {
  const ids: string[] = [];
  for (const m of text.matchAll(CITATION)) {
    const vid = normalizeVerseId(`${m[1]}.${m[2]}`);
    if (vid && !ids.includes(vid)) ids.push(vid);
  }
  return ids;
}

/**
 * Split a multi-question answer at its "### n. <sub-question>" headings. Null unless there are at
 * least two numbered sections within range, so unexpected formats fall back to one section.
 */
function splitAnswerSections(text: string, questionCount: number) {
  const matches = [...text.matchAll(/^###\s*(\d+)\.\s.*$/gm)];
  if (matches.length < 2) return null;
  const sections = matches.map((m, k) => ({
    index: parseInt(m[1], 10) - 1,
    text: text.slice(m.index ?? 0, k + 1 < matches.length ? matches[k + 1].index : text.length).trim(),
  }));
  if (sections.some((s) => s.index < 0 || s.index >= questionCount)) return null;
  return { intro: text.slice(0, matches[0].index).trim(), sections };
}

/** The backend's warning codes in plain words. Repeated "removed" warnings are counted, not listed. */
function warningNotes(warnings: string[] | undefined): string[] {
  if (!warnings?.length) return [];
  const notes: string[] = [];
  const removed = warnings.filter((w) => w === REMOVED_STATEMENT).length;
  if (removed === 1) notes.push('One statement the verses didn’t support was removed from this answer.');
  if (removed > 1) notes.push(`${removed} statements the verses didn’t support were removed from this answer.`);
  if (warnings.includes('truncated')) notes.push('This answer reached its length limit, so it may end early.');
  for (const w of warnings) {
    if (w !== REMOVED_STATEMENT && w !== 'truncated' && !notes.includes(w)) notes.push(w);
  }
  return notes;
}

interface Section {
  key: string;
  text: string;
  cards: Source[];
  shared: string[];
}

/** Text sections and the verse cards each one cites (every verse shown once, under its first citation) */
function buildSections(msg: ChatMessage): { intro: string; sections: Section[]; nearby: Source[] } {
  const sources = msg.sources ?? [];
  const byId = new Map(sources.map((s) => [normalizeVerseId(s.verse_id) ?? s.verse_id, s]));
  const split = (msg.subQuestions?.length ?? 0) > 1 && sources.length > 0
    ? splitAnswerSections(msg.text, msg.subQuestions!.length)
    : null;
  const parts = split ? split.sections.map((s) => ({ key: `s${s.index}`, text: s.text })) : [{ key: 'all', text: msg.text }];

  const shown = new Set<string>();
  const sections = parts.map(({ key, text }) => {
    const ids = citedVerseIds(text);
    const cards = ids.filter((id) => byId.has(id) && !shown.has(id)).map((id) => byId.get(id)!);
    const shared = ids.filter((id) => byId.has(id) && shown.has(id));
    cards.forEach((s) => shown.add(normalizeVerseId(s.verse_id) ?? s.verse_id));
    return { key, text, cards, shared };
  });
  const nearby = sources
    .filter((s) => !shown.has(normalizeVerseId(s.verse_id) ?? s.verse_id))
    .sort((a, b) => Number(!!a.is_neighbor) - Number(!!b.is_neighbor))
    .slice(0, NEARBY_LIMIT);
  return { intro: split?.intro ?? '', sections, nearby };
}

interface VerseGroupProps {
  label: string;
  verses: Source[];
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

/** A collapsible row of verse cards: "Show 2 verses · BG 2.47, BG 2.48" */
function VerseGroup({ label, verses, open, onToggle, children }: VerseGroupProps) {
  const ids = verses.map((s) => `BG ${s.verse_id}`).join(', ');
  return (
    <div className="verse-group mt-3 rounded-xl border border-[#C5A059]/25 bg-[#FAF6EB]/60">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-left text-xs text-[#704B20] transition-colors hover:bg-[#F4ECE1]/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <BookOpen className="h-3.5 w-3.5 shrink-0 text-[#E28743]" aria-hidden="true" />
          <span className="font-semibold">{open ? 'Hide' : 'Show'} {label}</span>
          <span className="truncate font-cinzel text-[11px] text-[#8C2D19]">· {ids}</span>
        </span>
        <ChevronDown className={`h-3.5 w-3.5 shrink-0 transition-transform duration-200 motion-reduce:transition-none ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>
      {open && <div className="space-y-2 border-t border-[#C5A059]/15 p-2">{children}</div>}
    </div>
  );
}

interface AssistantAnswerProps {
  msg: ChatMessage;
  isLoading: boolean;
  onSendMessage: (query: string) => void;
  onOpenVerseDetail: (verseId: string) => void;
  onOpenQuoteCard: (verseId: string) => void;
}

/**
 * One VYOM answer: Markdown sections with clickable (BG x.y) chips, each section's verse cards in a
 * collapsible group, then up to 3 related verses. A chip opens its group, scrolls the message list
 * (never the page) to the card and highlights it once; a verse without a card opens the verse modal.
 */
export function AssistantAnswer({ msg, isLoading, onSendMessage, onOpenVerseDetail, onOpenQuoteCard }: AssistantAnswerProps) {
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const [highlight, setHighlight] = useState<string | null>(null);
  const pendingScroll = useRef<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const { intro, sections, nearby } = buildSections(msg);

  const groupOf = new Map<string, string>();
  sections.forEach((sec) => sec.cards.forEach((s) => groupOf.set(normalizeVerseId(s.verse_id) ?? s.verse_id, sec.key)));
  nearby.forEach((s) => groupOf.set(normalizeVerseId(s.verse_id) ?? s.verse_id, 'nearby'));
  const cardKey = (vid: string) => `${msg.id}:${vid}`;

  const showVerse = (vid: string) => {
    const group = groupOf.get(vid);
    if (!group) {
      onOpenVerseDetail(vid);
      return;
    }
    setOpenGroups((prev) => (prev[group] ? prev : { ...prev, [group]: true }));
    pendingScroll.current = cardKey(vid);
    setHighlight(cardKey(vid));
  };

  // After the group has opened: scroll the message list to the card, then end the highlight
  useEffect(() => {
    if (!highlight) return;
    const key = pendingScroll.current;
    pendingScroll.current = null;
    const card = key ? rootRef.current?.querySelector<HTMLElement>(`[data-verse-card="${CSS.escape(key)}"]`) : null;
    const area = card?.closest<HTMLElement>('.overflow-y-auto');
    if (card && area) {
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const top = card.getBoundingClientRect().top - area.getBoundingClientRect().top + area.scrollTop - 16;
      area.scrollTo({ top, behavior: reduce ? 'auto' : 'smooth' });
      card.focus({ preventScroll: true });
    }
    const timer = window.setTimeout(() => setHighlight(null), HIGHLIGHT_MS);
    return () => window.clearTimeout(timer);
  }, [highlight]);

  const renderText: TextRenderer = (text, key) => {
    const out: React.ReactNode[] = [];
    let last = 0;
    let n = 0;
    for (const m of text.matchAll(CITATION)) {
      const vid = normalizeVerseId(`${m[1]}.${m[2]}`);
      if (!vid || m.index === undefined) continue;
      if (m.index > last) out.push(text.slice(last, m.index));
      out.push(
        <button
          key={`${key}-c${n++}`}
          type="button"
          onClick={() => showVerse(vid)}
          aria-label={`Show verse BG ${vid}`}
          className="mx-0.5 inline-flex items-center rounded-md border border-[#C5A059]/45 bg-[#F4ECE1]/80 px-1.5 align-baseline font-cinzel text-[12px] font-semibold leading-5 text-[#8C2D19] transition-colors hover:border-[#A27427] hover:bg-[#F1E0BB]/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
        >
          BG {vid}
        </button>,
      );
      last = m.index + m[0].length;
    }
    if (last < text.length) out.push(text.slice(last));
    return out.length === 1 ? out[0] : <React.Fragment key={key}>{out}</React.Fragment>;
  };

  const toggle = (group: string) => setOpenGroups((prev) => ({ ...prev, [group]: !prev[group] }));
  const cards = (list: Source[]) =>
    list.map((s) => {
      const vid = normalizeVerseId(s.verse_id) ?? s.verse_id;
      return (
        <VerseCard
          key={s.verse_id}
          source={s}
          cardKey={cardKey(vid)}
          highlighted={highlight === cardKey(vid)}
          onOpenVerseDetail={onOpenVerseDetail}
          onOpenQuoteCard={onOpenQuoteCard}
        />
      );
    });
  const countLabel = (n: number) => `${n} ${n === 1 ? 'verse' : 'verses'}`;
  const hasSources = (msg.sources?.length ?? 0) > 0;

  return (
    <div ref={rootRef} className="space-y-1">
      {intro && <AnswerMarkdown text={intro} renderText={renderText} />}
      {sections.map((sec) => (
        <section key={sec.key} className="pb-3">
          <AnswerMarkdown text={sec.text} renderText={renderText} />
          {sec.cards.length > 0 && (
            <VerseGroup label={countLabel(sec.cards.length)} verses={sec.cards} open={!!openGroups[sec.key]} onToggle={() => toggle(sec.key)}>
              {cards(sec.cards)}
            </VerseGroup>
          )}
          {sec.shared.length > 0 && (
            <p className="mt-2 text-[11px] italic text-[#6A5A48]">
              Also draws on {sec.shared.map((id) => `BG ${id}`).join(', ')}, shown above.
            </p>
          )}
        </section>
      ))}

      {/* Small-talk reply ("hi"): no verses, just ways to begin */}
      {msg.routed === 'smalltalk' && <SuggestionChips onSelectQuery={onSendMessage} disabled={isLoading} />}

      {nearby.length > 0 && (
        <VerseGroup label={`${nearby.length} related ${nearby.length === 1 ? 'verse' : 'verses'}`} verses={nearby} open={!!openGroups.nearby} onToggle={() => toggle('nearby')}>
          {cards(nearby)}
        </VerseGroup>
      )}

      {/* Answers without sources (the welcome message): plain verse chips */}
      {!hasSources && (msg.citedVerses?.length ?? 0) > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-[#C5A059]/15 pt-3">
          <span className="flex items-center gap-1 font-cinzel text-[10px] font-bold uppercase tracking-wider text-[#A27427]">
            <BookOpen className="h-3 w-3 text-[#E28743]" aria-hidden="true" /> {msg.chipsLabel ?? 'Cited Verses'}:
          </span>
          {msg.citedVerses!.map((ref) => {
            const vid = normalizeVerseId(ref);
            if (!vid) return null;
            return (
              <span key={vid} className="inline-flex items-center rounded-lg border border-[#C5A059]/30 bg-[#F4ECE1] shadow-sm transition-colors hover:border-[#E28743]/70">
                <button
                  type="button"
                  onClick={() => onOpenVerseDetail(vid)}
                  className="flex items-center gap-1 px-2.5 py-1 font-cinzel text-xs font-semibold text-[#8C2D19] hover:text-[#2C261F] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
                >
                  <span>BG {vid}</span>
                  <ArrowUpRight className="h-3 w-3 opacity-60" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={() => onOpenQuoteCard(vid)}
                  aria-label={`Quote card for BG ${vid}`}
                  className="border-l border-[#C5A059]/20 p-1 text-[#A27427] transition-colors hover:bg-[#FFFDF8] hover:text-[#2C261F] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
                >
                  <Share2 className="h-3 w-3" aria-hidden="true" />
                </button>
              </span>
            );
          })}
        </div>
      )}

      {/* Notes from the backend's checks (quote verifier, length limit): quiet, not an alarm */}
      {warningNotes(msg.warnings).map((note) => (
        <p key={note} className="mt-4 flex items-start gap-1.5 text-xs leading-5 text-[#6A5A48]">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#A27427]" aria-hidden="true" />
          <span>{note}</span>
        </p>
      ))}
    </div>
  );
}
