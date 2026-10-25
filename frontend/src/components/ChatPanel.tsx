import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  BookOpen,
  Volume2,
  Copy,
  Check,
  AlertCircle,
  Share2,
  Flame,
  ArrowUpRight,
} from 'lucide-react';
import { lookupVerse, type GitaVerse } from '../data/gitaVerses';
import { SanskritAudio } from '../services/audioChant';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citedVerses?: string[];
  routed?: boolean;
  timestamp: string;
  isOfflineFallback?: boolean;
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

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onOpenVerseDetail,
  onOpenQuoteCard,
  errorBannerText,
  onDismissError,
}) => {
  const [inputText, setInputText] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [playingVerse, setPlayingVerse] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleCopyMessage = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleChantVerse = (verseId: string) => {
    const v = lookupVerse(verseId);
    if (!v) return;

    if (playingVerse === verseId) {
      SanskritAudio.stop();
      setPlayingVerse(null);
    } else {
      setPlayingVerse(verseId);
      SanskritAudio.playShlokaChant(v.sanskrit, v.transliteration, () => {
        setPlayingVerse(null);
      });
    }
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
            className="font-cinzel text-sm md:text-base font-bold text-[#C5A059] mt-4 mb-2 tracking-wide flex items-center gap-2"
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
            className="my-1.5 pl-3.5 py-1 border-l-2 border-[#C5A059]/60 bg-[#FFFDF8]/40 rounded-r-lg font-cinzel text-xs md:text-sm text-[#2C261F] italic"
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
        <p key={idx} className="font-sans-body text-xs md:text-sm leading-relaxed text-[#2C261F]/90 my-1">
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
          <em key={i} className="italic text-[#6A5A48]">
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
        <div className="relative px-4 py-3 bg-gradient-to-r from-[#2A1D0B] via-[#38260E] to-[#2A1D0B] border-b border-[#C5A059]/40 text-[#2C261F] flex items-center justify-between shadow-md animate-fade-in">
          <div className="flex items-center gap-2.5">
            <span className="p-1 rounded-full bg-[#E28743]/20 border border-[#E28743]/40">
              <AlertCircle className="w-4 h-4 text-[#E28743]" />
            </span>
            <p className="font-cinzel text-xs font-medium tracking-wide">
              {errorBannerText}
            </p>
          </div>
          <button
            onClick={onDismissError}
            className="text-xs text-[#C5A059] hover:text-[#2C261F] font-cinzel underline ml-3"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.sender === 'user' ? 'items-end' : 'items-start'
            } transition-all`}
          >
            {/* Sender Badge */}
            <div className="flex items-center gap-1.5 mb-1.5 text-[11px] font-cinzel text-[#6A5A48]/70">
              {msg.sender === 'user' ? (
                <>
                  <span>You (Seeker)</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#C5A059]" />
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-[#E28743]" />
                  <span className="font-bold text-[#C5A059]">
                    VYOM Intelligence
                  </span>
                  {msg.isOfflineFallback && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] bg-amber-500/10 border border-amber-500/20 text-amber-300">
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
              className={`max-w-[92%] sm:max-w-[85%] rounded-2xl p-4 sm:p-5 relative group transition-all ${
                msg.sender === 'user'
                  ? 'bg-gradient-to-br from-[#EDE3D2] to-[#F4ECE1] border border-[#C5A059]/30 text-[#2C261F] rounded-tr-none shadow-md'
                  : 'bg-gradient-to-br from-[#FFFDF8]/95 via-[#FFFDF8]/95 to-[#F4ECE1]/95 border border-[#C5A059]/25 text-[#2C261F] rounded-tl-none shadow-xl'
              }`}
            >
              {/* Message Content */}
              {msg.sender === 'user' ? (
                <p className="font-sans-body text-sm text-[#2C261F] leading-relaxed">
                  {msg.text}
                </p>
              ) : (
                <div className="space-y-1">
                  {formatGitaResponse(msg.text)}

                  {/* Cited Verses Bar */}
                  {msg.citedVerses && msg.citedVerses.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-[#C5A059]/15 flex flex-wrap items-center gap-2">
                      <span className="font-cinzel text-[10px] uppercase tracking-wider text-[#C5A059]/80 font-bold flex items-center gap-1">
                        <BookOpen className="w-3 h-3 text-[#E28743]" /> Cited Verses:
                      </span>

                      {msg.citedVerses.map((vid) => {
                        const verseObj = lookupVerse(vid);
                        const isThisChanting = playingVerse === vid;

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

                            {/* Audio Chant Button */}
                            <button
                              onClick={() => handleChantVerse(vid)}
                              title={isThisChanting ? 'Stop Chant' : 'Listen to Sanskrit Shloka'}
                              className={`p-1 border-l border-[#C5A059]/20 transition-colors ${
                                isThisChanting
                                  ? 'bg-[#E28743] text-[#F4ECE1]'
                                  : 'text-[#C5A059] hover:text-[#2C261F] hover:bg-[#FFFDF8]'
                              }`}
                            >
                              <Volume2 className="w-3 h-3" />
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
                  )}
                </div>
              )}

              {/* Action Buttons (Copy) */}
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleCopyMessage(msg.id, msg.text)}
                  title="Copy response"
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

        {/* Loading Spinner / Meditation animation */}
        {isLoading && (
          <div className="flex flex-col items-start space-y-2 animate-pulse">
            <div className="flex items-center gap-2 text-xs font-cinzel text-[#C5A059]">
              <Sparkles className="w-4 h-4 text-[#E28743] animate-spin" style={{ animationDuration: '3s' }} />
              <span>Contemplating the Eternal Verse...</span>
            </div>
            <div className="p-4 rounded-2xl bg-[#FFFDF8]/80 border border-[#C5A059]/20 max-w-sm rounded-tl-none flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-[#E28743] animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 rounded-full bg-[#C5A059] animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 rounded-full bg-[#C5A059] animate-bounce" style={{ animationDelay: '300ms' }} />
              <span className="font-cinzel text-xs text-[#6A5A48]/80 italic ml-2">
                Grounding in Kurukshetra dialogue...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-4 border-t border-[#C5A059]/20 bg-[#F4ECE1]/90 backdrop-blur-md">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            ref={inputRef}
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isLoading}
            placeholder="Inquire of Lord Krishna... (e.g. 'Explain BG 2.47' or 'How to overcome grief?')"
            className="w-full py-3.5 pl-4 pr-14 rounded-xl bg-[#FFFDF8] border border-[#C5A059]/30 focus:border-[#E28743] focus:ring-1 focus:ring-[#E28743] text-sm text-[#2C261F] placeholder-[#6A5A48]/40 outline-none transition-all shadow-inner font-sans-body"
          />

          <button
            type="submit"
            disabled={!inputText.trim() || isLoading}
            className="absolute right-2 p-2.5 rounded-lg bg-gradient-to-r from-[#E28743] to-[#C5A059] text-[#F4ECE1] hover:brightness-110 active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md"
            title="Send Inquiry"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
