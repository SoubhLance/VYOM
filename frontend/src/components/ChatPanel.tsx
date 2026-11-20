import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { Sparkles, Copy, Check, AlertCircle, RotateCcw, Flame, X, ArrowDown } from 'lucide-react';
import { askErrorText, type AskErrorKind, type AskMeta, type Source } from '../services/api';
import { InspirationPanel, SuggestionChips } from './SuggestedChips';
import { VyomLogo } from './VyomLogo';
import { useModalFocus } from '../utils/useModalFocus';
import { ChatComposer } from './chat/ChatComposer';
import { AssistantAnswer } from './chat/AssistantAnswer';
import { markdownToPlainText } from './chat/markdown';
import { useChatScroll } from './chat/useChatScroll';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citedVerses?: string[];
  routed?: boolean | string;
  timestamp: string;
  subQuestions?: string[];
  warnings?: string[];
  sources?: Source[];
  /** Label for the verse chips when there are no rich sources (default "Cited Verses") */
  chipsLabel?: string;
  /** Set when the question failed: the message is an error note with Retry, never an answer */
  error?: { kind: AskErrorKind; status?: number; query: string };
  /** Debug headers of the response (cache, provider, model) */
  meta?: AskMeta;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (query: string) => void;
  onStop: () => void;
  onRetry: (messageId: string, query: string) => void;
  onOpenVerseDetail: (verseId: string) => void;
  onOpenQuoteCard: (verseId: string) => void;
}

/**
 * Debug mode: add ?debug=1 to the URL once (remembered in this browser; ?debug=0 turns it off).
 * Shows each answer's cache / provider / model from the response headers.
 */
const DEBUG = (() => {
  try {
    const flag = new URLSearchParams(window.location.search).get('debug');
    if (flag !== null) localStorage.setItem('vyom.debug', flag === '0' ? '0' : '1');
    return localStorage.getItem('vyom.debug') === '1';
  } catch {
    return false;
  }
})();

function DebugBadge({ msg }: { msg: ChatMessage }) {
  const m = msg.meta;
  const parts = msg.routed === 'smalltalk'
    ? ['small talk · no LLM']
    : [m?.cache && `cache ${m.cache}`, m?.provider, m?.model, m?.fallback && 'fallback'].filter(Boolean);
  if (parts.length === 0) return null;
  return (
    <span className="ml-1 rounded-md border border-dashed border-[#C5A059]/50 px-1.5 py-0.5 font-mono text-[10px] text-[#6A5A48]" title="Debug info (?debug=0 hides it)">
      {parts.join(' · ')}
    </span>
  );
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onStop,
  onRetry,
  onOpenVerseDetail,
  onOpenQuoteCard,
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  // Answers already here when the panel mounted (restored history) appear at once; new ones fade in
  const [restoredIds] = useState(() => new Set(messages.map((m) => m.id)));
  const [isInspireOpen, setIsInspireOpen] = useState(false);
  const closeInspire = () => setIsInspireOpen(false);
  const sheetRef = useModalFocus<HTMLDivElement>(isInspireOpen, closeInspire);

  const { scrollRef, onScroll, showJump, jumpToLatest } = useChatScroll(messages, isLoading);

  const sendInspiration = (query: string) => {
    setIsInspireOpen(false);
    onSendMessage(query);
  };


  // Copies clean text: no Markdown symbols
  const handleCopyMessage = (id: string, text: string) => {
    navigator.clipboard.writeText(markdownToPlainText(text)).then(
      () => {
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      },
      () => { /* clipboard blocked: nothing to confirm */ },
    );
  };

  // Screen readers hear a short note when a new answer arrives (errors announce themselves via role="alert")
  const last = messages[messages.length - 1];
  const verseCount = last?.sources?.length ?? 0;
  const announcement =
    last && last.sender === 'assistant' && !last.error && !restoredIds.has(last.id)
      ? `VYOM has answered${verseCount ? `, with ${verseCount} ${verseCount === 1 ? 'verse' : 'verses'}` : ''}.`
      : '';

  return (
    <div className="flex flex-col h-full rounded-2xl filigree-card overflow-hidden shadow-2xl border border-[#C5A059]/20">
      <p className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</p>
      {/* Messages Scroll Area */}
      <div className="relative min-h-0 flex-1">
      <div ref={scrollRef} onScroll={onScroll} className="h-full overflow-y-auto overscroll-contain px-3 py-5 sm:px-8 sm:py-7">
        {messages.length === 0 && !isLoading && (
          // Start screen: the VYOM mark, one line, and ways to begin (replaces the old stored welcome answer)
          <div className="mx-auto flex min-h-full max-w-[640px] flex-col items-center justify-center gap-4 py-6 text-center">
            <VyomLogo size="lg" showSubtitle={false} />
            <p className="max-w-md text-[15px] leading-7 text-[#4B3825]">
              Ask about duty, fear, loss or any verse. VYOM answers from the Bhagavad Gita’s own words.
            </p>
            <div className="flex justify-center [&>div]:justify-center">
              <SuggestionChips onSelectQuery={onSendMessage} />
            </div>
          </div>
        )}
        <div className="mx-auto max-w-[760px] space-y-8 pb-4">
        {messages.map((msg, msgIndex) => msg.error ? (
          <div key={msg.id} data-message-id={msg.id} className="chat-msg-in flex flex-col items-start">
            {/* A failed or stopped question: an honest note, no answer-shaped content */}
            <div
              role={msg.error.kind === 'aborted' ? undefined : 'alert'}
              className="flex w-full flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-[#C5A059]/35 bg-[#F4ECE1]/80 px-4 py-3 text-sm text-[#2C261F]"
            >
              <AlertCircle className={`h-4 w-4 shrink-0 ${msg.error.kind === 'aborted' ? 'text-[#6A5A48]' : 'text-[#E28743]'}`} aria-hidden="true" />
              <p className="min-w-0 flex-1">{askErrorText(msg.error.kind, msg.error.status)}</p>
              {msgIndex === messages.length - 1 && (
                <button
                  type="button"
                  onClick={() => onRetry(msg.id, msg.error?.query ?? '')}
                  disabled={isLoading}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-[#C5A059]/45 bg-[#FFFDF8] px-3 py-1.5 text-xs font-semibold text-[#704B20] transition hover:border-[#A27427] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60 disabled:opacity-50"
                >
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Retry
                </button>
              )}
            </div>
          </div>
        ) : (
          <div
            key={msg.id}
            data-message-id={msg.id}
            className={`chat-msg-in group flex flex-col ${
              msg.sender === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            {msg.sender === 'assistant' && (
              <div className="mb-2 flex items-center gap-1.5 font-cinzel text-[11px] text-[#6A5A48]">
                <Sparkles className="h-3.5 w-3.5 text-[#E28743]" aria-hidden="true" />
                <span className="font-bold text-[#8C2D19]">VYOM</span>
              </div>
            )}

            <div
              title={msg.timestamp}
              className={msg.sender === 'user'
                ? 'max-w-[85%] rounded-2xl rounded-br-md border border-[#C5A059]/45 bg-[#F4ECE1] px-4 py-2.5 text-[#2C261F]'
                : `w-full text-[#2C261F] ${restoredIds.has(msg.id) ? '' : 'answer-reveal'}`}
            >
              {msg.sender === 'user' ? (
                <p className="whitespace-pre-wrap break-words font-sans-body text-[15px] leading-relaxed">
                  <span className="sr-only">You asked: </span>
                  {msg.text}
                </p>
              ) : (
                <AssistantAnswer
                  msg={msg}
                  isLoading={isLoading}
                  onSendMessage={onSendMessage}
                  onOpenVerseDetail={onOpenVerseDetail}
                  onOpenQuoteCard={onOpenQuoteCard}
                />
              )}

            </div>

            {/* Answer actions: visible on hover / keyboard focus, always on touch screens */}
            {msg.sender === 'assistant' && (
              <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity duration-200 focus-within:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100">
                <button
                  type="button"
                  onClick={() => handleCopyMessage(msg.id, msg.text)}
                  aria-label={copiedId === msg.id ? 'Copied' : 'Copy answer'}
                  title="Copy answer"
                  className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-[#6A5A48] transition-colors hover:bg-[#F4ECE1] hover:text-[#2C261F] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
                >
                  {copiedId === msg.id ? <Check className="h-3.5 w-3.5 text-[#A27427]" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
                  <span>{copiedId === msg.id ? 'Copied' : 'Copy'}</span>
                </button>
                {DEBUG && <DebugBadge msg={msg} />}
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator: a softly flickering diya */}
        {isLoading && (
          <div className="chat-msg-in flex w-fit items-center gap-3 py-1" role="status">
            <Flame className="chat-diya h-4 w-4 text-[#E28743]" aria-hidden="true" />
            <span className="font-cinzel text-xs tracking-wide text-[#6A5A48]">Contemplating the verses…</span>
          </div>
        )}
        </div>
      </div>

      </div>

      {/* Input Bar */}
      <div className="border-t border-[#C5A059]/20 bg-[#F4ECE1]/95 px-3 pb-[max(0.625rem,env(safe-area-inset-bottom))] pt-3 sm:px-6">
        <ChatComposer isLoading={isLoading} onSend={onSendMessage} onStop={onStop} onInspire={() => setIsInspireOpen(true)} />
        {/* While the reader has scrolled up, the footnote line becomes "Jump to latest": it lives in the input
            bar, outside the messages, so it never covers a verse card at any width */}
        <div className="mx-auto mt-1.5 flex h-5 max-w-[760px] items-center justify-center">
          {showJump ? (
            <button
              type="button"
              onClick={jumpToLatest}
              className="animate-fade-in inline-flex items-center gap-1 rounded-full px-2 text-[11px] font-semibold text-[#704B20] underline-offset-2 transition hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
            >
              <ArrowDown className="h-3 w-3" aria-hidden="true" /> Jump to latest
            </button>
          ) : (
            <p className="text-center text-[11px] text-[#796A57]">Grounded in sacred verses and traditional commentaries</p>
          )}
        </div>
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
