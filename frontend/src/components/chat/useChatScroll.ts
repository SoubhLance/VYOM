import { useCallback, useLayoutEffect, useRef, useState } from 'react';

/** Within this many px of the bottom counts as "at the latest message" */
const NEAR_BOTTOM_PX = 96;

interface ScrollableMessage {
  id: string;
  sender: 'user' | 'assistant';
}

const prefersReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/**
 * Scrolling for the message list (scrolls only the list, never the page):
 * - follows new messages only while the reader is at the bottom; scrolling up stops it
 * - your own question always scrolls into view
 * - a new answer scrolls so its first line is at the top (a long answer is read from its start)
 * - showJump is true while the reader is away from the bottom ("Jump to latest")
 * Elements need data-message-id attributes.
 */
export function useChatScroll(messages: ScrollableMessage[], isLoading: boolean) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const followRef = useRef(true);
  const seenCountRef = useRef<number | null>(null);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = useCallback((smooth: boolean) => {
    const area = scrollRef.current;
    if (!area) return;
    // Smooth only for short hops; crossing a long conversation smoothly takes over a second
    const distance = area.scrollHeight - area.scrollTop - area.clientHeight;
    const animate = smooth && !prefersReducedMotion() && distance < area.clientHeight * 2;
    area.scrollTo({ top: area.scrollHeight, behavior: animate ? 'smooth' : 'auto' });
  }, []);

  const onScroll = useCallback(() => {
    const area = scrollRef.current;
    if (!area) return;
    const near = area.scrollHeight - area.scrollTop - area.clientHeight < NEAR_BOTTOM_PX;
    followRef.current = near;
    setShowJump((prev) => (prev === !near ? prev : !near));
  }, []);

  useLayoutEffect(() => {
    const area = scrollRef.current;
    if (!area) return;
    const seen = seenCountRef.current;
    seenCountRef.current = messages.length;

    // First render (history restored from this browser): start at the latest message, no animation
    if (seen === null) {
      scrollToBottom(false);
      return;
    }

    const last = messages[messages.length - 1];
    if (messages.length > seen && last) {
      if (last.sender === 'user') {
        followRef.current = true;
        scrollToBottom(true);
        return;
      }
      if (!followRef.current) return;
      const el = area.querySelector<HTMLElement>(`[data-message-id="${CSS.escape(last.id)}"]`);
      if (el && el.offsetHeight > area.clientHeight * 0.6) {
        // Long answer: put its start at the top instead of jumping to its end
        const top = el.getBoundingClientRect().top - area.getBoundingClientRect().top + area.scrollTop - 12;
        area.scrollTo({ top, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
      } else {
        scrollToBottom(true);
      }
      return;
    }
    // Messages removed (new conversation, retry) or the thinking indicator appeared
    if (messages.length < seen || (isLoading && followRef.current)) scrollToBottom(true);
  }, [messages, isLoading, scrollToBottom]);

  const jumpToLatest = useCallback(() => {
    followRef.current = true;
    scrollToBottom(true);
  }, [scrollToBottom]);

  return { scrollRef, onScroll, showJump, jumpToLatest };
}
