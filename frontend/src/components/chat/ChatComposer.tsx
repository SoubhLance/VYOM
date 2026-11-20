import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Send, Sparkles, Square } from 'lucide-react';

/** Longest question we send. The backend has no limit; this keeps prompts (and Groq tokens) sane. */
export const MAX_QUESTION_LENGTH = 1000;
/** The counter appears once the question gets this long */
const COUNTER_FROM = 800;
/** The box grows with the text up to about six lines, then scrolls */
const MAX_HEIGHT_PX = 168;

interface ChatComposerProps {
  isLoading: boolean;
  onSend: (query: string) => void;
  onStop: () => void;
  onInspire: () => void;
}

/**
 * Question box: grows with the text, Enter sends, Shift+Enter adds a line (safe with IME / Devanagari
 * keyboards), stays editable while VYOM answers so the next question can be drafted, and turns its
 * send button into Stop while loading. Keeps its own state so typing re-renders only this form.
 */
export function ChatComposer({ isLoading, onSend, onStop, onInspire }: ChatComposerProps) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const query = text.trim();
  const canSend = query.length > 0 && !isLoading;

  // Grow with the content (reset first so it can also shrink)
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT_PX ? 'auto' : 'hidden';
  }, [text]);

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

  // Esc stops a running answer from anywhere on the page, unless a dialog is open (Esc closes that)
  useEffect(() => {
    if (!isLoading) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || event.defaultPrevented) return;
      if (document.querySelector('[role="dialog"][aria-modal="true"]')) return;
      event.preventDefault();
      onStop();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isLoading, onStop]);

  const send = () => {
    if (!canSend) return;
    onSend(query);
    setText('');
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter while an IME is composing (Devanagari, CJK...) confirms the composition, never sends
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send();
    } else if (event.key === 'Escape' && text && !isLoading) {
      // While loading, Esc means Stop (window listener above); otherwise it clears the draft
      event.preventDefault();
      setText('');
    }
  };

  const showCounter = text.length >= COUNTER_FROM;

  return (
    <form
      onSubmit={(event) => { event.preventDefault(); send(); }}
      className="mx-auto flex max-w-[760px] items-end gap-2"
    >
      <button
        type="button"
        onClick={onInspire}
        className="inline-flex h-12 shrink-0 items-center gap-1.5 rounded-xl border border-[#C5A059]/35 bg-[#FFFDF8] px-3 text-xs font-semibold text-[#704B20] transition hover:border-[#A27427] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60 xl:hidden"
        aria-haspopup="dialog"
        aria-label="Inspiration: themes and sacred inquiries"
        title="Themes and sacred inquiries"
      >
        <Sparkles className="h-4 w-4 text-[#E28743]" aria-hidden="true" />
        <span className="hidden sm:inline">Inspire</span>
      </button>
      <div className="relative min-w-0 flex-1">
        <textarea
          ref={inputRef}
          rows={1}
          value={text}
          maxLength={MAX_QUESTION_LENGTH}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Your question"
          aria-describedby={showCounter ? 'vyom-question-counter' : undefined}
          placeholder="Ask a question, or 'Explain BG 2.47'"
          enterKeyHint="send"
          className="block min-h-12 w-full resize-none rounded-xl border border-[#C5A059]/35 bg-[#FFFDF8] py-3 pl-4 pr-14 font-sans-body text-base leading-6 text-[#2C261F] placeholder-[#6A5A48]/70 shadow-inner outline-none transition focus:border-[#C5A059] focus:ring-4 focus:ring-[#C5A059]/20 sm:text-[15px]"
        />
        <div className="absolute bottom-1.5 right-1.5">
          {isLoading ? (
            <button
              type="button"
              onClick={onStop}
              className="rounded-lg border border-[#8C2D19]/40 bg-[#FFFDF8] p-2.5 text-[#8C2D19] transition-colors hover:bg-[#F4ECE1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/60"
              title="Stop (Esc)"
              aria-label="Stop answering"
              aria-keyshortcuts="Escape"
            >
              <Square className="h-4 w-4 fill-current" aria-hidden="true" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!canSend}
              className="rounded-lg bg-gradient-to-r from-[#E28743] to-[#C5A059] p-2.5 text-[#FFFDF8] shadow-md transition-all hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8C2D19]/60 focus-visible:ring-offset-1 active:scale-95 disabled:cursor-not-allowed disabled:opacity-30 motion-reduce:active:scale-100"
              title="Send"
              aria-label="Send question"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
        {showCounter && (
          <p id="vyom-question-counter" className="mt-1 text-right text-[11px] text-[#6A5A48]" aria-live="polite">
            {text.length} / {MAX_QUESTION_LENGTH}
          </p>
        )}
      </div>
    </form>
  );
}
