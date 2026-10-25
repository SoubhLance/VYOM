import { useState, useEffect, useCallback, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { ChatPanel, type ChatMessage } from './components/ChatPanel';
import { SuggestedChips } from './components/SuggestedChips';
import { VerseDetailModal } from './components/VerseDetailModal';
import { QuoteCardModal } from './components/QuoteCardModal';
import { AboutModal } from './components/AboutModal';
import { VyomLogo } from './components/VyomLogo';
import { SacredAtmosphere } from './components/SacredAtmosphere';
import { lookupVerse, type GitaVerse } from './data/gitaVerses';
import { askGitaQuestion, checkBackendHealth } from './services/api';
import { SanskritAudio } from './services/audioChant';
import { BookOpen, Volume2, Sparkles } from 'lucide-react';

const pillars = [
  { id: '2.47', name: 'Nishkama Karma', note: 'Action without attachment' },
  { id: '18.66', name: 'Charama Shloka', note: 'The path of surrender' },
  { id: '2.20', name: 'Atma Tattva', note: 'The eternal nature of self' },
  { id: '4.7', name: 'Avatara Rahasya', note: 'The return of dharma' },
  { id: '6.35', name: 'Abhyasa Yoga', note: 'Practice and a steady mind' },
];
const themes = ['Surrender & Anxiety', 'Nishkama Karma in Modern Life', 'Conquering Self-Doubt', 'Decision Making in Dilemma'];

export function App() {
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [isChanting, setIsChanting] = useState(false);
  const [hasEnteredPortal, setHasEnteredPortal] = useState(false);
  const [gatewayFading, setGatewayFading] = useState(false);
  const [backgroundVideoFailed, setBackgroundVideoFailed] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const transitionStarted = useRef(false);
  const [activeVerse, setActiveVerse] = useState<GitaVerse | null>(null);
  const [isVerseModalOpen, setIsVerseModalOpen] = useState(false);
  const [quoteVerse, setQuoteVerse] = useState<GitaVerse | null>(null);
  const [isQuoteModalOpen, setIsQuoteModalOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [errorBannerText, setErrorBannerText] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([{
    id: 'welcome-1', sender: 'assistant',
    text: '### Welcome, seeker\n\nBring a question about duty, relationships, fear, or the nature of the self. I will draw on the Bhagavad Gita and its traditional commentaries to help you reflect.\n\nBegin with a sacred inquiry below, or share what is on your mind.',
    citedVerses: ['2.47', '18.66'], timestamp: 'Welcome',
  }]);

  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    try { setIsBackendOnline((await checkBackendHealth()).online); }
    finally { setIsCheckingHealth(false); }
  }, []);
  useEffect(() => {
    if (!hasEnteredPortal) return;
    void checkHealth();
    const interval = window.setInterval(() => void checkHealth(), 30000);
    return () => window.clearInterval(interval);
  }, [hasEnteredPortal, checkHealth]);
  useEffect(() => { if (audioRef.current) audioRef.current.volume = 0.2; }, []);

  const beginTransition = useCallback(() => {
    if (transitionStarted.current) return;
    transitionStarted.current = true;
    setGatewayFading(true);
    const audio = audioRef.current;
    if (audio) void audio.play().then(() => setIsAudioPlaying(true)).catch(() => setIsAudioPlaying(false));
    window.setTimeout(() => setHasEnteredPortal(true), 800);
  }, []);
  useEffect(() => {
    if (hasEnteredPortal) return;
    let fallback: number | undefined;
    const handleVisibility = () => {
      if (document.hidden) fallback = window.setTimeout(beginTransition, 5000);
      else if (fallback !== undefined) { window.clearTimeout(fallback); fallback = undefined; }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => { document.removeEventListener('visibilitychange', handleVisibility); if (fallback !== undefined) window.clearTimeout(fallback); };
  }, [hasEnteredPortal, beginTransition]);

  const handleToggleAudio = async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isAudioPlaying) { audio.pause(); setIsAudioPlaying(false); }
    else { try { await audio.play(); setIsAudioPlaying(true); } catch { setIsAudioPlaying(false); } }
  };
  const toggleChant = () => {
    if (isChanting) { SanskritAudio.stop(); setIsChanting(false); return; }
    const verse = lookupVerse('2.47');
    if (verse) { setIsChanting(true); SanskritAudio.playShlokaChant(verse.sanskrit, verse.transliteration, () => setIsChanting(false)); }
  };
  const openVerse = (id: string) => { const verse = lookupVerse(id); if (verse) { setActiveVerse(verse); setIsVerseModalOpen(true); } };
  const handleOpenQuoteCard = (verse: GitaVerse) => { setQuoteVerse(verse); setIsQuoteModalOpen(true); };
  const handleSendMessage = async (queryText: string) => {
    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, sender: 'user', text: queryText, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
    setIsLoading(true); setErrorBannerText(null);
    try {
      const response = await askGitaQuestion({ query: queryText, top_k: 5 });
      setMessages((prev) => [...prev, { id: `assistant-${Date.now()}`, sender: 'assistant', text: response.answer, citedVerses: response.cited_verses, routed: response.routed, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), isOfflineFallback: response.isOfflineFallback }]);
    } catch (err) {
      setErrorBannerText(err instanceof Error ? err.message : 'The consultation service is temporarily unavailable.');
      setMessages((prev) => [...prev, { id: `assistant-${Date.now()}`, sender: 'assistant', text: '### A moment for reflection\n\nWhile the consultation service reconnects, remember **BG 2.47**: focus on sincere action, without attachment to its results.', citedVerses: ['2.47'], timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), isOfflineFallback: true }]);
    } finally { setIsLoading(false); }
  };
  const handleThemeSelect = (theme: string) => {
    const prompts: Record<string, string> = {
      'Surrender & Anxiety': 'How can the Bhagavad Gita help me meet anxiety through surrender? Explain BG 18.66.',
      'Nishkama Karma in Modern Life': 'How can I practice Nishkama Karma in modern life? Explain BG 2.47.',
      'Conquering Self-Doubt': 'How can Krishna’s teachings help me overcome self-doubt?',
      'Decision Making in Dilemma': 'How should I make a difficult decision when I feel torn between duties?',
    };
    void handleSendMessage(prompts[theme] ?? theme);
  };

  return (
    <div className="relative isolate min-h-screen bg-[#FAF6EB] text-[#2C261F] selection:bg-[#D4AF37]/25 selection:text-[#1F1D1A]">
      <audio ref={audioRef} src="/bg_music.mp3" loop preload="none" onPause={() => setIsAudioPlaying(false)} onPlay={() => setIsAudioPlaying(true)} />
      {!hasEnteredPortal ? <div className={`fixed inset-0 z-50 overflow-hidden transition-opacity duration-[800ms] ${gatewayFading ? 'opacity-0' : 'opacity-100'}`}>
        {backgroundVideoFailed && <img src="/kurukshetra_hero.jpg" alt="" aria-hidden="true" className="absolute inset-0 h-full w-full object-cover" />}
        <video autoPlay muted playsInline loop={false} onEnded={beginTransition} aria-hidden="true" className={`fixed inset-0 w-full h-full object-cover -z-20 pointer-events-none ${backgroundVideoFailed ? 'hidden' : ''}`} onError={(event) => { const video = event.currentTarget; if (!video.dataset.fallback) { video.dataset.fallback = 'true'; video.src = '/bg_vyom.mp4'; video.load(); } else { setBackgroundVideoFailed(true); beginTransition(); } }}>
          <source src="/favicon/bg_vyom.mp4" type="video/mp4" />
        </video>
        <div aria-hidden="true" className="absolute inset-0 bg-gradient-to-b from-[#21170f]/35 via-[#21170f]/20 to-[#21170f]/60" />
        <div className="absolute right-5 top-5 z-10"><button onClick={beginTransition} className="rounded-full border border-[#F5E6C8]/50 bg-[#34291ecc] px-4 py-2 text-xs font-medium text-[#FFF9EA] backdrop-blur-md transition hover:bg-[#57462c]">Skip gateway <span aria-hidden="true">→</span></button></div>
        <div className="absolute inset-x-0 bottom-9 z-10 flex flex-col items-center gap-3 text-center text-[#FFF9EA] drop-shadow-lg"><VyomLogo size="md" showSubtitle={false} /><span className="font-cinzel text-xs tracking-[0.22em]">Bhagavad Gita Multimodal Intelligence</span><span className="text-xs text-[#FFF9EA]/75">Entering the sanctuary…</span></div>
      </div> : <>
        <SacredAtmosphere />
        <Navbar isBackendOnline={isBackendOnline} isCheckingHealth={isCheckingHealth} onRefreshHealth={checkHealth} isAudioPlaying={isAudioPlaying} onToggleAudio={handleToggleAudio} onOpenAbout={() => setIsAboutOpen(true)} onToggleChant={toggleChant} isChanting={isChanting} />
        <main className="relative z-10 mx-auto grid w-full max-w-[1440px] flex-1 grid-cols-1 gap-5 px-4 py-6 sm:px-6 lg:grid-cols-[270px_minmax(0,1fr)] lg:px-8">
          <aside className="space-y-4">
            <section className="royal-card rounded-2xl p-5"><p className="font-cinzel text-[10px] font-bold uppercase tracking-[0.18em] text-[#8C2D19]">Your quick sanctuary</p><h2 className="mt-1 font-cinzel text-lg font-bold text-[#4B3825]">Five Gita pillars</h2><div className="mt-4 space-y-2">{pillars.map((pillar) => <button key={pillar.id} onClick={() => openVerse(pillar.id)} className="group w-full rounded-xl border border-[#D4AF37]/20 bg-white/65 p-3 text-left transition hover:border-[#C5A059]/70 hover:bg-[#fffdf8]"><span className="flex items-center justify-between"><span className="font-cinzel text-xs font-bold text-[#8C2D19]">BG {pillar.id}</span><BookOpen className="h-3.5 w-3.5 text-[#C5A059]" /></span><span className="mt-1 block text-sm font-semibold text-[#2C261F]">{pillar.name}</span><span className="mt-0.5 block text-xs text-[#6A5A48]">{pillar.note}</span></button>)}</div></section>
            <section className="royal-card rounded-2xl p-5"><div className="flex items-center gap-2"><span className="rounded-lg bg-[#F2E6D0] p-2 text-[#A27427]"><Volume2 className="h-4 w-4" /></span><div><h3 className="font-cinzel text-sm font-bold text-[#4B3825]">Sacred listening</h3><p className="text-xs text-[#766653]">A verse, softly recited</p></div></div><button onClick={toggleChant} className="mt-4 w-full rounded-xl border border-[#C5A059]/45 bg-gradient-to-r from-[#FBF4E4] to-[#F3E4C7] px-4 py-2.5 text-sm font-semibold text-[#704B20] transition hover:shadow-md">{isChanting ? 'Stop BG 2.47 chant' : 'Listen to BG 2.47'}</button></section>
            <section className="rounded-2xl border border-[#D4AF37]/25 bg-[#fffdf8]/65 p-4 text-center"><Sparkles className="mx-auto h-4 w-4 text-[#B89343]" /><p className="mt-2 font-sanskrit text-sm text-[#8C2D19]" lang="sa">योगः कर्मसु कौशलम्</p><p className="mt-1 text-[11px] text-[#766653]">Yoga is skill in action · BG 2.50</p></section>
          </aside>

          <section className="min-w-0 space-y-4">
            <header className="royal-card rounded-2xl px-5 py-5 sm:px-7"><p className="font-cinzel text-[10px] uppercase tracking-[0.2em] text-[#9A6B27]">A quiet place to reflect</p><h1 className="mt-1 font-cinzel text-2xl font-bold text-[#4B3825] sm:text-3xl">Ask the Eternal Charioteer</h1><p className="mt-1 font-sanskrit text-sm text-[#8C2D19]" lang="sa">श्रीमद्भगवद्गीतायाः प्रज्ञया परामर्शं प्राप्नुहि</p><p className="mt-2 text-sm text-[#665746]">Bring your question. Find perspective in the timeless dialogue of the Gita.</p></header>
            <div className="flex flex-wrap gap-2">{themes.map((theme) => <button key={theme} onClick={() => handleThemeSelect(theme)} disabled={isLoading} className="rounded-full border border-[#C5A059]/35 bg-[#fffdf8]/85 px-3.5 py-2 text-xs font-semibold text-[#704B20] shadow-sm transition hover:-translate-y-0.5 hover:border-[#B89343] hover:bg-white disabled:opacity-50">{theme}</button>)}</div>
            <section className="h-[min(70vh,850px)] min-h-[540px]" aria-label="Gita consultation"><ChatPanel messages={messages} isLoading={isLoading} onSendMessage={handleSendMessage} onOpenVerseDetail={(verse) => { setActiveVerse(verse); setIsVerseModalOpen(true); }} onOpenQuoteCard={handleOpenQuoteCard} errorBannerText={errorBannerText} onDismissError={() => setErrorBannerText(null)} /></section>
            <section className="flex flex-wrap items-center justify-between gap-3 px-1"><p className="text-[11px] text-[#796A57]">Grounded in sacred verses and traditional commentaries</p><SuggestedChips onSelectQuery={handleSendMessage} disabled={isLoading} /></section>
          </section>
        </main>
        <footer className="relative z-10 border-t border-[#C5A059]/20 bg-[#FAF6EB]/75 py-3 text-center text-[11px] text-[#796A57]">© {new Date().getFullYear()} VYOM · Bhagavad Gita Multimodal Intelligence</footer>
        <VerseDetailModal verse={activeVerse} isOpen={isVerseModalOpen} onClose={() => setIsVerseModalOpen(false)} onOpenQuoteCard={handleOpenQuoteCard} />
        <QuoteCardModal verse={quoteVerse} isOpen={isQuoteModalOpen} onClose={() => setIsQuoteModalOpen(false)} />
        <AboutModal isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />
      </>}
    </div>
  );
}

export default App;
