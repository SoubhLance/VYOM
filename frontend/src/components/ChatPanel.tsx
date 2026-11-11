import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  Send,
  Sparkles,
  BookOpen,
  Copy,
  Check,
  AlertCircle,
  Share2,
  Flame,
  ArrowUpRight,
  X,
} from 'lucide-react';
import { lookupVerse, type GitaVerse } from '../data/gitaVerses';
import type { Source } from '../services/api';
import { ClipPlayer } from './ClipPlayer';
import { InspirationPanel } from './SuggestedChips';
import { useModalFocus } from '../utils/useModalFocus';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citedVerses?: string[];
  routed?: boolean | string;
  timestamp: string;
  isOfflineFallback?: boolean;
  subQuestions?: string[];
  warnings?: string[];
  sources?: Source[];
  /** Label for the verse chips when there are no rich sources (default "Cited Verses") */
  chipsLabel?: string;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (query: string) => void;
  onOpenVerseDetail: (verse: GitaVerse) => void;
  onOpenQuoteCard: (verse: GitaVerse) => void;
  errorBannerText: string | null;
  onDismissError: () => void;
}

interface ChatComposerProps {
  isLoading: boolean;
  onSend: (query: string) => void;
  onInspire: () => void;
}

/** The input keeps its own state, so each keystroke re-renders only this form, not every answer above it. */
function ChatComposer({ isLoading, onSend, onInspire }: ChatComposerProps) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // "/" jumps to the question box unless the user is already typing somewhere or a dialog is open
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey) return;
      const target = event.target;
      if (target instanceof Element && target.closest('input, textarea, select, [contenteditable="true"], [role="dialog"]')) return;
      if (document.querySelector('[role="dialog"][aria-modal="true"]')) return;
      event.preventDefault();
      inputRef.current?.focus();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const query = text.trim();
    if (!query || isLoading) return;
    onSend(query);
    setText('');
  };
  return (
    <form onSubmit={submit} className="relative mx-auto flex max-w-3xl items-center gap-2">
      <button
        type="button"
        onClick={onInspire}
        className="inline-flex h-12 shrink-0 items-center gap-1.5 rounded-xl border border-[#C5A059]/35 bg-[#FFFDF8] px-3 text-xs font-semibold text-[#704B20] transition hover:border-[#A27427] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/50 xl:hidden"
        aria-haspopup="dialog"
        title="Themes and sacred inquiries"
      >
        <Sparkles className="h-4 w-4 text-[#E28743]" />
        <span className="hidden sm:inline">Inspire</span>
      </button>
      <input
        ref={inputRef}
        type="text"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Escape' && text) { event.preventDefault(); setText(''); } }}
        disabled={isLoading}
        aria-label="Your question"
        placeholder="Ask a question, or 'Explain BG 2.47'  ( / )"
        className="h-12 w-full min-w-0 rounded-xl border border-[#C5A059]/35 bg-[#FFFDF8] pl-4 pr-14 font-sans-body text-[15px] text-[#2C261F] placeholder-[#6A5A48]/60 shadow-inner outline-none transition focus:border-[#C5A059] focus:ring-4 focus:ring-[#C5A059]/20"
      />
      <button
        type="submit"
        disabled={!text.trim() || isLoading}
        className="absolute right-1.5 p-2.5 rounded-lg bg-gradient-to-r from-[#E28743] to-[#C5A059] text-[#F4ECE1] hover:brightness-110 active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md"
        title="Send Inquiry"
      >
        <Send className="w-4 h-4" />
      </button>
    </form>
  );
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onOpenVerseDetail,
  onOpenQuoteCard,
  errorBannerText,
  onDismissError,
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const [isInspireOpen, setIsInspireOpen] = useState(false);
  const closeInspire = () => setIsInspireOpen(false);
  const sheetRef = useModalFocus<HTMLDivElement>(isInspireOpen, closeInspire);

  // Scroll only the message list (scrollIntoView also scrolled the whole page)
  useEffect(() => {
    const area = scrollAreaRef.current;
    if (!area) return;
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    area.scrollTo({ top: area.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  }, [messages, isLoading]);

  const sendInspiration = (query: string) => {
    setIsInspireOpen(false);
    onSendMessage(query);
  };


  const handleCopyMessage = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  /** Verse ids cited in a piece of answer text, in order of first appearance */
  const citedVerseIds = (text: string): string[] => {
    const ids: string[] = [];
    const re = /\bBG\s*([1-9]|1[0-8])[.:]([1-9]|[1-6][0-9]|7[0-8])\b/gi;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const vid = `${parseInt(m[1], 10)}.${parseInt(m[2], 10)}`;
      if (!ids.includes(vid)) ids.push(vid);
    }
    return ids;
  };

  /**
   * Split a multi-question answer at its "### n. <sub-question>" headings.
   * Returns null unless there are at least two numbered sections within range,
   * so unexpected formats fall back to the plain layout.
   */
  const splitAnswerSections = (text: string, questionCount: number) => {
    const matches = [...text.matchAll(/^###\s*(\d+)\.\s.*$/gm)];
    if (matches.length < 2) return null;
    const sections = matches.map((m, k) => ({
      index: parseInt(m[1], 10) - 1,
      text: text.slice(m.index ?? 0, k + 1 < matches.length ? matches[k + 1].index : text.length).trim(),
    }));
    if (sections.some((s) => s.index < 0 || s.index >= questionCount)) return null;
    return { intro: text.slice(0, matches[0].index).trim(), sections };
  };

  const NEARBY_LIMIT = 3;

  /** Related verses not cited in the answer: collapsed, at most NEARBY_LIMIT, in retrieval order */
  const renderNearby = (sources: Source[]) => {
    const nearby = sources.slice(0, NEARBY_LIMIT);
    if (nearby.length === 0) return null;
    return (
      <details className="group rounded-xl border border-[#C5A059]/25 bg-[#FAF6EB]/50 p-2.5 transition-all text-xs">
        <summary className="font-cinzel font-semibold text-[#8C2D19] cursor-pointer list-none flex items-center justify-between select-none py-0.5">
          <span className="flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5 text-[#E28743]" />
            Nearby verses ({nearby.length})
          </span>
          <span className="text-[10px] text-[#A27427] font-sans group-open:rotate-180 transition-transform">▼</span>
        </summary>
        <div className="mt-2.5 space-y-2 pt-2 border-t border-[#C5A059]/15">{nearby.map(renderSourceCard)}</div>
      </details>
    );
  };

  const renderSourceCard = (s: Source) => {
    const verseObj = lookupVerse(s.verse_id);

    return (
      <div
        key={s.verse_id}
        className="rounded-xl border border-[#C5A059]/30 bg-[#FFFDF8]/90 p-3 space-y-2 shadow-sm transition-all hover:border-[#C5A059]/60"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-cinzel text-xs font-bold text-[#8C2D19] bg-[#F1E0BB]/60 px-2 py-0.5 rounded-md border border-[#C5A059]/30">
              BG {s.verse_id}
            </span>
            {s.is_neighbor && s.neighbor_of && (
              <span className="text-[10px] font-cinzel text-[#6A5A48] italic">(Context for BG {s.neighbor_of})</span>
            )}
          </div>
          {verseObj && (
            <button
              onClick={() => onOpenVerseDetail(verseObj)}
              className="text-[11px] font-cinzel font-semibold text-[#8C2D19] hover:text-[#2C261F] flex items-center gap-1 transition-colors"
              title="View full verse details"
            >
              <span>Exposition</span>
              <ArrowUpRight className="w-3 h-3 opacity-70" />
            </button>
          )}
        </div>

        {s.sanskrit && (
          <p className="font-sanskrit text-xs text-[#2C261F] leading-relaxed" lang="sa">
            {s.sanskrit}
          </p>
        )}

        {s.transliteration && <p className="iast text-xs leading-relaxed">{s.transliteration}</p>}

        {s.clips && s.clips.length > 0 && <ClipPlayer clips={s.clips} />}
      </div>
    );
  };

  /**
   * Format message text into styled paragraphs, quotes, and headings
   */
  const formatGitaResponse = (rawText: string) => {
    const lines = rawText.split('\n');
    return lines.map((line, idx) => {
      // Headings
      if (line.startsWith('### ')) {
        return (
          <h4
            key={idx}
            className="font-cinzel text-[15px] md:text-base font-bold text-[#8C2D19] mt-5 mb-2 tracking-wide flex items-center gap-2 first:mt-0"
          >
            <Flame className="w-3.5 h-3.5 text-[#E28743]" />
            {line.replace('### ', '')}
          </h4>
        );
      }
      if (line.startsWith('## ')) {
        return (
          <h3
            key={idx}
            className="font-cinzel text-base md:text-lg font-bold text-[#2C261F] mt-5 mb-2.5 tracking-wide"
          >
            {line.replace('## ', '')}
          </h3>
        );
      }

      // Blockquotes (Shlokas & translations)
      if (line.startsWith('> ')) {
        return (
          <blockquote
            key={idx}
            className="iast my-2 pl-4 py-1.5 border-l-2 border-[#C5A059]/60 bg-[#F4ECE1]/50 rounded-r-lg text-sm md:text-[15px] leading-relaxed"
          >
            {line.replace('> ', '')}
          </blockquote>
        );
      }

      // Empty lines
      if (!line.trim()) {
        return <div key={idx} className="h-2" />;
      }

      // Regular paragraph with bold highlighting
      return (
        <p key={idx} className="font-sans-body text-[15px] leading-7 text-[#2C261F] my-1.5">
          {renderFormattedInline(line)}
        </p>
      );
    });
  };

  // Basic inline formatting for **bold** and *italic*
  const renderFormattedInline = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*|\*.*?\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-[#8C2D19]">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('*') && part.endsWith('*')) {
        return (
          <em key={i} className="iast">
            {part.slice(1, -1)}
          </em>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex flex-col h-full rounded-2xl filigree-card overflow-hidden shadow-2xl border border-[#C5A059]/20">
      {/* Serene Golden Banner for 502 / Error Masking */}
      {errorBannerText && (
        <div role="alert" className="relative px-4 py-3 bg-[#F4ECE1] border-b border-[#E28743]/40 text-[#8C2D19] flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-2.5">
            <span className="p-1 rounded-full bg-[#E28743]/20 border border-[#E28743]/40">
              <AlertCircle className="w-4 h-4 text-[#E28743]" />
            </span>
            <p className="text-[13px] font-medium">
              {errorBannerText}
            </p>
          </div>
          <button
            onClick={onDismissError}
            className="ml-3 shrink-0 rounded-lg px-2 py-1 text-xs font-semibold text-[#704B20] underline-offset-2 hover:bg-[#FFFDF8] hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div ref={scrollAreaRef} className="flex-1 overflow-y-auto overscroll-contain px-3 py-5 sm:px-8 sm:py-7">
        <div className="mx-auto max-w-3xl space-y-7">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-msg-in flex flex-col ${
              msg.sender === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            {/* Sender Badge */}
            <div className="flex items-center gap-1.5 mb-1.5 text-[11px] font-cinzel text-[#6A5A48]/70">
              {msg.sender === 'user' ? (
                <span>You</span>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-[#E28743]" />
                  <span className="font-bold text-[#8C2D19]">VYOM</span>
                  {msg.isOfflineFallback && (
                    <span className="rounded border border-[#E28743]/40 bg-[#E28743]/10 px-1.5 py-0.5 font-sans text-[10px] font-semibold text-[#8C2D19]">
                      Offline Mode
                    </span>
                  )}
                </>
              )}
              <span className="text-[10px] text-[#6A5A48]/40 ml-1">
                {msg.timestamp}
              </span>
            </div>

            {/* Bubble */}
            <div
              className={`relative group ${
                msg.sender === 'user'
                  ? 'max-w-[85%] rounded-2xl rounded-br-md bg-[#4B3825] px-4 py-2.5 text-[#FAF6EB] shadow-sm'
                  : 'w-full rounded-2xl rounded-tl-md border border-[#C5A059]/25 border-l-[3px] border-l-[#C5A059] bg-[#FFFDF8]/95 px-4 py-4 text-[#2C261F] shadow-[0_10px_30px_rgba(180,140,75,0.08)] sm:px-6 sm:py-5'
              }`}
            >
              {/* Message Content */}
              {msg.sender === 'user' ? (
                <p className="font-sans-body text-[15px] leading-relaxed text-[#FAF6EB]">
                  {msg.text}
                </p>
              ) : (
                <div className="space-y-1">
                  {(() => {
                    const sectioned = (msg.subQuestions?.length ?? 0) > 1 && msg.sources && msg.sources.length > 0
                      ? splitAnswerSections(msg.text, msg.subQuestions!.length)
                      : null;
                    if (!sectioned) return formatGitaResponse(msg.text);

                    // Each section, then the verse cards it cites (each verse shown once)
                    const sources = msg.sources ?? [];
                    const shown = new Set<string>();
                    return (
                      <>
                        {sectioned.intro && formatGitaResponse(sectioned.intro)}
                        {sectioned.sections.map((sec) => {
                          const ids = citedVerseIds(sec.text);
                          const cards = sources.filter((s) => ids.includes(s.verse_id) && !shown.has(s.verse_id));
                          const sharedHere = sources.filter((s) => ids.includes(s.verse_id) && shown.has(s.verse_id));
                          cards.forEach((s) => shown.add(s.verse_id));
                          return (
                            <section key={sec.index} className="space-y-2 pb-2">
                              <div className="space-y-1">{formatGitaResponse(sec.text)}</div>
                              {cards.length > 0 && <div className="grid grid-cols-1 gap-2">{cards.map(renderSourceCard)}</div>}
                              {sharedHere.length > 0 && (
                                <p className="text-[11px] text-[#6A5A48] italic">
                                  Also draws on {sharedHere.map((s) => `BG ${s.verse_id}`).join(', ')}, shown above.
                                </p>
                              )}
                            </section>
                          );
                        })}
                        {renderNearby(sources.filter((s) => !shown.has(s.verse_id)))}
                      </>
                    );
                  })()}

                  {/* Warning Note when quotes failed strict verification */}
                  {msg.warnings && msg.warnings.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-[#C5A059]/15 flex items-center gap-1.5 text-[11px] font-cinzel text-amber-800/80 italic">
                      <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                      <span>
                        {msg.warnings.some((w) => w !== 'truncated')
                          ? 'Some quotes could not be checked against the translations'
                          : 'This answer was cut short'}
                      </span>
                    </div>
                  )}

                  {/* Sources / Cited Verses Bar */}
                  {(() => {
                    const hasSources = msg.sources && msg.sources.length > 0;
                    // Sectioned answers already placed their cards next to each section
                    if (hasSources && (msg.subQuestions?.length ?? 0) > 1 && splitAnswerSections(msg.text, msg.subQuestions!.length)) {
                      return null;
                    }

                    // Fallback to local gitaVerses data if backend sources array is empty
                    if (!hasSources) {
                      if (!msg.citedVerses || msg.citedVerses.length === 0) return null;

                      return (
                        <div className="mt-4 pt-3 border-t border-[#C5A059]/15 flex flex-wrap items-center gap-2">
                          <span className="font-cinzel text-[10px] uppercase tracking-wider text-[#C5A059]/80 font-bold flex items-center gap-1">
                            <BookOpen className="w-3 h-3 text-[#E28743]" /> {msg.chipsLabel ?? 'Cited Verses'}:
                          </span>

                          {msg.citedVerses.map((vid) => {
                            const verseObj = lookupVerse(vid);

                            return (
                              <div
                                key={vid}
                                className="inline-flex items-center rounded-lg bg-[#F4ECE1] border border-[#C5A059]/30 hover:border-[#E28743]/70 transition-all shadow-sm"
                              >
                                <button
                                  onClick={() => {
                                    if (verseObj) onOpenVerseDetail(verseObj);
                                  }}
                                  className="px-2.5 py-1 font-cinzel text-xs font-semibold text-[#8C2D19] hover:text-[#2C261F] flex items-center gap-1"
                                  title="Click to view full Sanskrit, transliteration and commentaries"
                                >
                                  <span>BG {vid}</span>
                                  <ArrowUpRight className="w-3 h-3 opacity-60" />
                                </button>

                                {/* Quote Card Trigger */}
                                {verseObj && (
                                  <button
                                    onClick={() => onOpenQuoteCard(verseObj)}
                                    title="Generate Royal Quote Card"
                                    className="p-1 border-l border-[#C5A059]/20 text-[#C5A059] hover:text-[#2C261F] hover:bg-[#FFFDF8] transition-colors"
                                  >
                                    <Share2 className="w-3 h-3" />
                                  </button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      );
                    }

                    // Rich multimodal RAG sources
                    const allSources = msg.sources ?? [];

                    // Extract verse numbers explicitly quoted in msg.text (e.g. (BG x.y) or BG x.y)
                    const quotedIdsList: string[] = [];
                    const quoteRegex = /\bBG\s*([1-9]|1[0-8])[.:]([1-9]|[1-6][0-9]|7[0-8])\b/gi;
                    let m: RegExpExecArray | null;
                    while ((m = quoteRegex.exec(msg.text)) !== null) {
                      const vid = `${parseInt(m[1], 10)}.${parseInt(m[2], 10)}`;
                      if (!quotedIdsList.includes(vid)) {
                        quotedIdsList.push(vid);
                      }
                    }
                    const quotedSet = new Set(quotedIdsList);

                    const quotedSources = allSources.filter((s) => quotedSet.has(s.verse_id));
                    const unquotedSources = allSources.filter((s) => !quotedSet.has(s.verse_id));

                    const hasQuoted = quotedSources.length > 0;
                    const primarySources = hasQuoted
                      ? quotedSources
                      : allSources.filter((s) => !s.is_neighbor);
                    const nearbySources = hasQuoted
                      ? unquotedSources
                      : allSources.filter((s) => s.is_neighbor);

                    const subQuestions = msg.subQuestions ?? [];
                    const hasMultipleQuestions = subQuestions.length > 1;

                    return (
                      <div className="mt-4 pt-3 border-t border-[#C5A059]/20 space-y-4">
                        {/* Primary Sources */}
                        {hasMultipleQuestions && subQuestions.some((_, i) => primarySources.some((s) => s.for_question?.includes(i))) ? (
                          <div className="space-y-4">
                            {subQuestions.map((sq, i) => {
                              // Show each verse once, under the first sub-question it serves
                              const qSources = primarySources.filter((s) => s.for_question?.includes(i) && Math.min(...(s.for_question ?? [i])) === i);
                              const sharedHere = primarySources.filter((s) => s.for_question?.includes(i) && Math.min(...(s.for_question ?? [i])) < i);
                              if (qSources.length === 0 && sharedHere.length === 0) return null;
                              return (
                                <div key={i} className="space-y-2">
                                  <h5 className="font-cinzel text-xs font-bold text-[#8C2D19] flex items-center gap-1.5 tracking-wide">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[#E28743]" />
                                    <span>Sub-Question {i + 1}: {sq}</span>
                                  </h5>
                                  <div className="grid grid-cols-1 gap-2">
                                    {qSources.map(renderSourceCard)}
                                  </div>
                                  {sharedHere.length > 0 && (
                                    <p className="text-[11px] text-[#6A5A48] italic">
                                      Also draws on {sharedHere.map((s) => `BG ${s.verse_id}`).join(', ')}, shown above.
                                    </p>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          primarySources.length > 0 && (
                            <div className="space-y-2">
                              <span className="font-cinzel text-[10px] uppercase tracking-wider text-[#C5A059]/90 font-bold flex items-center gap-1">
                                <BookOpen className="w-3 h-3 text-[#E28743]" /> Source Verses:
                              </span>
                              <div className="grid grid-cols-1 gap-2">
                                {primarySources.map(renderSourceCard)}
                              </div>
                            </div>
                          )
                        )}

                        {renderNearby(nearbySources)}
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Action Buttons (Copy) */}
              <div className="absolute top-2 right-2 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100 [@media(hover:none)]:opacity-100">
                <button
                  onClick={() => handleCopyMessage(msg.id, msg.text)}
                  title="Copy response"
                  aria-label="Copy response"
                  className="p-1.5 rounded-lg bg-[#F4ECE1]/80 border border-[#C5A059]/20 text-[#6A5A48] hover:text-[#2C261F] transition-colors"
                >
                  {copiedId === msg.id ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator: a softly flickering diya */}
        {isLoading && (
          <div className="chat-msg-in flex items-center gap-3 rounded-2xl rounded-tl-md border border-[#C5A059]/25 bg-[#FFFDF8]/90 px-4 py-3 w-fit" role="status">
            <Flame className="chat-diya h-4 w-4 text-[#E28743]" aria-hidden="true" />
            <span className="font-cinzel text-xs tracking-wide text-[#6A5A48]">Contemplating the verses…</span>
          </div>
        )}
        </div>
      </div>

      {/* Input Bar */}
      <div className="border-t border-[#C5A059]/20 bg-[#F4ECE1]/95 px-3 pb-2.5 pt-3 sm:px-6">
        <ChatComposer isLoading={isLoading} onSend={onSendMessage} onInspire={() => setIsInspireOpen(true)} />
        <p className="mx-auto mt-1.5 max-w-3xl text-center text-[11px] text-[#796A57]">Grounded in sacred verses and traditional commentaries</p>
      </div>

      {/* Inspiration sheet (below xl, where there is no side rail), portalled to <body> so no ancestor's
          filter or transform can trap position: fixed inside the chat card */}
      {isInspireOpen && createPortal(
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-[#4B3825]/45 xl:hidden" onMouseDown={(event) => { if (event.target === event.currentTarget) closeInspire(); }}>
          <div ref={sheetRef} role="dialog" aria-modal="true" aria-label="Inspiration" tabIndex={-1} className="chat-sheet-in relative max-h-[78dvh] w-full max-w-lg overflow-y-auto rounded-t-3xl border border-b-0 border-[#C5A059]/40 bg-[#FAF6EB] px-5 pb-8 pt-3 shadow-2xl outline-none">
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-[#C5A059]/50" aria-hidden="true" />
            <button onClick={closeInspire} aria-label="Close inspiration" className="absolute right-3 top-3 rounded-lg p-1.5 text-[#6A5A48] hover:bg-[#F4ECE1]"><X className="h-4 w-4" /></button>
            <InspirationPanel onSelectQuery={sendInspiration} disabled={isLoading} />
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
};
