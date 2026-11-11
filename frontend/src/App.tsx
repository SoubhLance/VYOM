import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react';
import { Navbar } from './components/Navbar';
import { ChatPanel, type ChatMessage } from './components/ChatPanel';
import { InspirationPanel } from './components/SuggestedChips';
import { VerseDetailModal } from './components/VerseDetailModal';
import { AboutModal } from './components/AboutModal';
import { VyomGateway } from './components/VyomGateway';
import { SacredAtmosphere } from './components/SacredAtmosphere';

// The reader carries the 701-verse directory (~380 kB), so it loads only when the book opens
// canvas-confetti and the card renderer load only when someone opens a quote card
const QuoteCardModal = lazy(() => import('./components/QuoteCardModal').then((m) => ({ default: m.QuoteCardModal })));
const GitaBookReader = lazy(() => import('./components/GitaBookReader').then((m) => ({ default: m.GitaBookReader })));

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome-1', sender: 'assistant',
  text: '### Welcome, seeker\n\nBring a question about duty, relationships, fear, or the nature of the self. I will draw on the Bhagavad Gita and its traditional commentaries to help you reflect.\n\nBegin with a sacred inquiry below, or share what is on your mind.',
  citedVerses: ['2.47', '18.66'], chipsLabel: 'Begin with', timestamp: 'Welcome',
};

// The conversation survives a refresh (this browser only); "New conversation" clears it
const HISTORY_KEY = 'vyom.chat.v1';
const MAX_SAVED_MESSAGES = 60;
function loadHistory(): ChatMessage[] {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? 'null');
    if (Array.isArray(saved) && saved.length > 0) return saved as ChatMessage[];
  } catch {
    /* storage blocked or corrupt: start fresh */
  }
  return [WELCOME_MESSAGE];
}

const CURRENT_YEAR = new Date().getFullYear();
const GATEWAY_MIN_MS = 1200;
const GATEWAY_MAX_MS = 3000;
import { lookupVerse, type GitaVerse } from './data/gitaVerses';
import { askGitaQuestion, checkBackendHealth } from './services/api';
import { onClipPlayStart, onClipPlayEndOrPause } from './services/audioCoordinator';
import { BookOpen, Volume2, Sparkles, Headphones, Plus } from 'lucide-react';

const pillars = [
  { id: '2.47', name: 'Nishkama Karma', note: 'Action without attachment' },
  { id: '18.66', name: 'Charama Shloka', note: 'The path of surrender' },
  { id: '2.20', name: 'Atma Tattva', note: 'The eternal nature of self' },
  { id: '4.7', name: 'Avatara Rahasya', note: 'The return of dharma' },
  { id: '6.35', name: 'Abhyasa Yoga', note: 'Practice and a steady mind' },
];

export function App() {
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [isPlaying247, setIsPlaying247] = useState(false);
  const verse247AudioRef = useRef<HTMLAudioElement | null>(null);
  const [hasEnteredPortal, setHasEnteredPortal] = useState(false);
  const [gatewayFading, setGatewayFading] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const transitionStarted = useRef(false);
  const sendInFlightRef = useRef(false);
  const [activeVerse, setActiveVerse] = useState<GitaVerse | null>(null);
  const [isVerseModalOpen, setIsVerseModalOpen] = useState(false);
  const [quoteVerse, setQuoteVerse] = useState<GitaVerse | null>(null);
  const [isQuoteModalOpen, setIsQuoteModalOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [activeView, setActiveView] = useState<'chat' | 'book'>('chat');
  const [bookInitialVerse, setBookInitialVerse] = useState<string | null>(null);
  const [errorBannerText, setErrorBannerText] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(loadHistory);

  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    try { setIsBackendOnline((await checkBackendHealth()).online); }
    finally { setIsCheckingHealth(false); }
  }, []);
  useEffect(() => {
    if (!hasEnteredPortal) return;
    const interval = window.setInterval(() => void checkHealth(), 30000);
    return () => window.clearInterval(interval);
  }, [hasEnteredPortal, checkHealth]);
  useEffect(() => { if (audioRef.current) audioRef.current.volume = 0.2; }, []);
  useEffect(() => {
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.slice(-MAX_SAVED_MESSAGES))); } catch { /* storage full or blocked */ }
  }, [messages]);
  const startNewConversation = () => {
    setMessages([WELCOME_MESSAGE]);
    setErrorBannerText(null);
  };

  const beginTransition = useCallback(() => {
    if (transitionStarted.current) return;
    transitionStarted.current = true;
    setGatewayFading(true);
    const audio = audioRef.current;
    if (audio) void audio.play().then(() => setIsAudioPlaying(true)).catch(() => setIsAudioPlaying(false));
    window.setTimeout(() => setHasEnteredPortal(true), 800);
  }, []);
  // Gateway: stay until fonts are ready and the first health check has settled (at least
  // GATEWAY_MIN_MS so it doesn't flash), but never longer than GATEWAY_MAX_MS. The backend never
  // blocks entry: if it is slow or down we proceed and the navbar shows offline.
  useEffect(() => {
    let cancelled = false;
    const started = performance.now();
    const maxTimer = window.setTimeout(beginTransition, GATEWAY_MAX_MS);
    const fontsReady = document.fonts?.ready ?? Promise.resolve();
    const health = checkBackendHealth().then((result) => { if (!cancelled) setIsBackendOnline(result.online); });
    void Promise.all([fontsReady, health]).then(() => {
      if (cancelled) return;
      const wait = Math.max(0, GATEWAY_MIN_MS - (performance.now() - started));
      window.setTimeout(() => { if (!cancelled) beginTransition(); }, wait);
    });
    return () => { cancelled = true; window.clearTimeout(maxTimer); };
  }, [beginTransition]);

  useEffect(() => {
    return () => {
      if (verse247AudioRef.current) {
        verse247AudioRef.current.pause();
      }
    };
  }, []);

  const handleToggleAudio = async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isAudioPlaying) { audio.pause(); setIsAudioPlaying(false); }
    else { try { await audio.play(); setIsAudioPlaying(true); } catch { setIsAudioPlaying(false); } }
  };
  const toggle247Audio = () => {
    if (!verse247AudioRef.current) {
      const audio = new Audio('/audio/verses/bg_02_47.mp3');
      audio.onplay = () => {
        setIsPlaying247(true);
        onClipPlayStart(audio);
      };
      audio.onpause = () => {
        setIsPlaying247(false);
        onClipPlayEndOrPause(audio);
      };
      audio.onended = () => {
        setIsPlaying247(false);
        onClipPlayEndOrPause(audio);
      };
      audio.onerror = () => {
        setIsPlaying247(false);
        onClipPlayEndOrPause(audio);
      };
      verse247AudioRef.current = audio;
    }

    const audio = verse247AudioRef.current;
    if (isPlaying247) {
      audio.pause();
    } else {
      audio.currentTime = 0;
      audio.play().catch(() => {
        setIsPlaying247(false);
      });
    }
  };
  const openVerse = (id: string) => { const verse = lookupVerse(id); if (verse) { setActiveVerse(verse); setIsVerseModalOpen(true); } };
  const handleOpenQuoteCard = (verse: GitaVerse) => { setQuoteVerse(verse); setIsQuoteModalOpen(true); };
  const handleSendMessage = async (queryText: string) => {
    // One request at a time: buttons disable on isLoading, but a double click can land before the re-render
    if (sendInFlightRef.current) return;
    sendInFlightRef.current = true;
    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, sender: 'user', text: queryText, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
    setIsLoading(true); setErrorBannerText(null);
    try {
      const response = await askGitaQuestion({ query: queryText, top_k: 5 });
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          sender: 'assistant',
          text: response.answer,
          citedVerses: response.cited_verses,
          routed: response.routed,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isOfflineFallback: response.isOfflineFallback,
          subQuestions: response.sub_questions,
          warnings: response.warnings,
          sources: response.sources,
        },
      ]);
    } catch (err) {
      setErrorBannerText(err instanceof Error ? err.message : 'The consultation service is temporarily unavailable.');
      setMessages((prev) => [...prev, { id: `assistant-${Date.now()}`, sender: 'assistant', text: '### A moment for reflection\n\nWhile the consultation service reconnects, remember **BG 2.47**: focus on sincere action, without attachment to its results.', citedVerses: ['2.47'], timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), isOfflineFallback: true }]);
    } finally { sendInFlightRef.current = false; setIsLoading(false); }
  };

  return (
    <div className={`relative isolate bg-[#FAF6EB] text-[#2C261F] selection:bg-[#D4AF37]/25 selection:text-[#1F1D1A] ${activeView === 'book' ? 'h-screen overflow-hidden flex flex-col' : 'min-h-screen'}`}>
      <audio ref={audioRef} src="/bg_music.mp3" loop preload="none" onPause={() => setIsAudioPlaying(false)} onPlay={() => setIsAudioPlaying(true)} />
      {!hasEnteredPortal ? <VyomGateway fading={gatewayFading} onSkip={beginTransition} /> : <>
        <SacredAtmosphere />
        <Navbar isBackendOnline={isBackendOnline} isCheckingHealth={isCheckingHealth} onRefreshHealth={checkHealth} isAudioPlaying={isAudioPlaying} onToggleAudio={handleToggleAudio} onOpenAbout={() => setIsAboutOpen(true)} onOpenBook={() => { setBookInitialVerse(null); setActiveView('book'); }} />
        {activeView === 'book' ? <Suspense fallback={<div className="relative z-10 flex flex-1 items-center justify-center py-24"><p className="royal-card rounded-2xl px-6 py-4 font-cinzel text-sm tracking-[0.18em] text-[#8C2D19]">Opening the scripture…</p></div>}><GitaBookReader key={bookInitialVerse ?? 'book'} initialVerseId={bookInitialVerse} onBack={() => setActiveView('chat')} /></Suspense> : <>
        <main className="relative z-10 mx-auto grid w-full max-w-[1500px] flex-1 grid-cols-1 gap-5 px-3 py-4 sm:px-6 sm:py-6 lg:grid-cols-[260px_minmax(0,1fr)] lg:px-8 xl:grid-cols-[260px_minmax(0,1fr)_280px]">
          <aside className="order-2 space-y-4 lg:order-none">
            <section className="royal-card rounded-2xl p-5"><p className="font-cinzel text-[10px] font-bold uppercase tracking-[0.18em] text-[#8C2D19]">Your quick sanctuary</p><h2 className="mt-1 font-cinzel text-lg font-bold text-[#4B3825]">Five Gita pillars</h2><div className="mt-4 space-y-2">{pillars.map((pillar) => <button key={pillar.id} onClick={() => openVerse(pillar.id)} className="group w-full rounded-xl border border-[#D4AF37]/20 bg-white/65 p-3 text-left transition hover:border-[#C5A059]/70 hover:bg-[#fffdf8]"><span className="flex items-center justify-between"><span className="font-cinzel text-xs font-bold text-[#8C2D19]">BG {pillar.id}</span><BookOpen className="h-3.5 w-3.5 text-[#C5A059]" /></span><span className="mt-1 block text-sm font-semibold text-[#2C261F]">{pillar.name}</span><span className="mt-0.5 block text-xs text-[#6A5A48]">{pillar.note}</span></button>)}</div></section>
            <section className="royal-card rounded-2xl p-5">
              <div className="flex items-center gap-2"><span className="rounded-lg bg-[#F2E6D0] p-2 text-[#A27427]"><Volume2 className="h-4 w-4" /></span><div><h3 className="font-cinzel text-sm font-bold text-[#4B3825]">Sacred listening</h3><p className="text-xs text-[#766653]">A verse, softly recited</p></div></div>
              <button onClick={toggle247Audio} className="mt-4 w-full rounded-xl border border-[#C5A059]/45 bg-gradient-to-r from-[#FBF4E4] to-[#F3E4C7] px-4 py-2.5 text-sm font-semibold text-[#704B20] transition hover:shadow-md">{isPlaying247 ? 'Stop BG 2.47 chant' : 'Listen to BG 2.47 chant'}</button>
              <button onClick={() => { setBookInitialVerse('2.47'); setActiveView('book'); }} className="mt-2.5 w-full rounded-xl border border-[#C5A059]/35 bg-white/70 px-4 py-2 text-xs font-semibold text-[#704B20] hover:border-[#A27427] hover:bg-[#fffdf8] transition flex items-center justify-center gap-1.5 shadow-sm"><Headphones className="w-3.5 h-3.5 text-[#E28743]" /><span>Explore All 701 Shlokas →</span></button>
            </section>
            <section className="rounded-2xl border border-[#D4AF37]/25 bg-[#fffdf8]/65 p-4 text-center"><Sparkles className="mx-auto h-4 w-4 text-[#B89343]" /><p className="mt-2 font-sanskrit text-sm text-[#8C2D19]" lang="sa">योगः कर्मसु कौशलम्</p><p className="mt-1 text-[11px] text-[#766653]">Yoga is skill in action · BG 2.50</p></section>
          </aside>

          <section className="flex min-w-0 flex-col gap-3">
            <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-1"><div><p className="font-cinzel text-[10px] uppercase tracking-[0.2em] text-[#9A6B27]">A quiet place to reflect</p><h1 className="font-cinzel text-xl font-bold text-[#4B3825] sm:text-2xl">Ask the Eternal Charioteer</h1></div><div className="flex items-center gap-3"><p className="hidden font-sanskrit text-sm text-[#8C2D19] sm:block" lang="sa">श्रीमद्भगवद्गीतायाः प्रज्ञया परामर्शं प्राप्नुहि</p>{messages.length > 1 && <button onClick={startNewConversation} disabled={isLoading} className="inline-flex items-center gap-1.5 rounded-full border border-[#C5A059]/40 bg-[#FFFDF8] px-3 py-1.5 text-xs font-semibold text-[#704B20] transition hover:border-[#A27427] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/50 disabled:opacity-50"><Plus className="h-3.5 w-3.5" />New conversation</button>}</div></header>
            <section className="h-[calc(100dvh-10.5rem)] min-h-[480px] lg:h-[calc(100dvh-12rem)]" aria-label="Gita consultation"><ChatPanel messages={messages} isLoading={isLoading} onSendMessage={handleSendMessage} onOpenVerseDetail={(verse) => { setActiveVerse(verse); setIsVerseModalOpen(true); }} onOpenQuoteCard={handleOpenQuoteCard} errorBannerText={errorBannerText} onDismissError={() => setErrorBannerText(null)} /></section>
          </section>

          <aside className="hidden xl:block" aria-label="Inspiration">
            <div className="royal-card sticky top-24 rounded-2xl p-5"><InspirationPanel onSelectQuery={handleSendMessage} disabled={isLoading} /></div>
          </aside>
        </main>
        <footer className="relative z-10 border-t border-[#C5A059]/20 bg-[#FAF6EB]/75 py-3 text-center text-[11px] text-[#796A57]">© {CURRENT_YEAR} VYOM · Bhagavad Gita Multimodal Intelligence</footer>
        <VerseDetailModal verse={activeVerse} isOpen={isVerseModalOpen} onClose={() => setIsVerseModalOpen(false)} onOpenQuoteCard={handleOpenQuoteCard} />
        {isQuoteModalOpen && <Suspense fallback={null}><QuoteCardModal verse={quoteVerse} isOpen={isQuoteModalOpen} onClose={() => setIsQuoteModalOpen(false)} /></Suspense>}
        <AboutModal isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />
        </>}
      </>}
    </div>
  );
}

export default App;
