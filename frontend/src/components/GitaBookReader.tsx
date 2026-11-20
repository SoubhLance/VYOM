import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent, type TouchEvent as ReactTouchEvent } from 'react';
import { ArrowLeft, BookOpen, ChevronLeft, ChevronRight, List, Pause, Play, Search, Volume2, X } from 'lucide-react';
// Verse text and translations: canonical data (verses.jsonl -> public/verses + public/translations).
// SHLOKA_DIRECTORY is used only for navigation order and the audio clip of each verse, never for text.
import { loadChapterVerses, type ChapterVerses } from '../data/verseStore';
import { CHAPTER_METAS, SHLOKA_DIRECTORY } from '../data/recitationIndex';
import { splitIastSpeaker, splitSanskritSpeaker } from '../utils/speaker';
import { onClipPlayEndOrPause, onClipPlayStart } from '../services/audioCoordinator';
import { BookCoverArt } from './BookCoverArt';
import './GitaBookReader.css';

interface GitaBookReaderProps {
  onBack: () => void;
  initialVerseId?: string | null;
}

const getVerseParts = (id: string | null | undefined) => {
  const match = id?.match(/^(\d{1,2})[.:](\d{1,3})$/);
  if (!match) return null;
  const chapter = Number(match[1]);
  const verse = Number(match[2]);
  return chapter >= 1 && chapter <= 18 ? { chapter, verse } : null;
};

const sanskritChapterTitles = [
  'अर्जुनविषादयोग', 'साङ्ख्ययोग', 'कर्मयोग', 'ज्ञानकर्मसंन्यासयोग',
  'कर्मसंन्यासयोग', 'आत्मसंयमयोग', 'ज्ञानविज्ञानयोग', 'अक्षरब्रह्मयोग',
  'राजविद्याराजगुह्ययोग', 'विभूतियोग', 'विश्वस्वरूपदर्शनयोग', 'भक्तियोग',
  'क्षेत्रक्षेत्रज्ञविभागयोग', 'गुणत्रयविभागयोग', 'पुरुषोत्तमयोग',
  'दैवासुरसम्पद्विभागयोग', 'श्रद्धात्रयविभागयोग', 'मोक्षसंन्यासयोग',
];

/** The verse to open at, if it exists in the directory ("Explore all shlokas" passes e.g. '2.47'). */
const findInitialVerse = (id: string | null | undefined) => {
  const parts = getVerseParts(id);
  return parts && SHLOKA_DIRECTORY.some((item) => item.chapter === parts.chapter && item.verseNumber === parts.verse) ? parts : null;
};

export function GitaBookReader({ onBack, initialVerseId }: GitaBookReaderProps) {
  const [initialVerse] = useState(() => findInitialVerse(initialVerseId));
  const [chapter, setChapter] = useState(initialVerse?.chapter ?? 1);
  const [verseNumber, setVerseNumber] = useState(initialVerse?.verse ?? 1);
  const [search, setSearch] = useState('');
  // Phones: the verse search is one tap away (a toolbar icon) instead of taking a whole toolbar row
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [continuous, setContinuous] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentPlayingId, setCurrentPlayingId] = useState<string | null>(null);
  const [isContentsOpen, setIsContentsOpen] = useState(false);
  // Opened at a specific verse: start on the open pages (the cover is one click away)
  const [isBookOpen, setIsBookOpen] = useState(initialVerse !== null);
  const [hasBookTransitioned, setHasBookTransitioned] = useState(false);
  // Chapters whose verse files have arrived (verseStore caches the fetch; render reads only this state)
  const [loadedChapters, setLoadedChapters] = useState<Record<number, ChapterVerses>>({});
  const [chapterLoadErrorFor, setChapterLoadErrorFor] = useState<number | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [selectedTranslationAuthor, setSelectedTranslationAuthor] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const continuousRef = useRef(continuous);
  const currentIdRef = useRef(initialVerse ? `${initialVerse.chapter}.${initialVerse.verse}` : '1.1');
  const activeChapterItemRef = useRef<HTMLDivElement | null>(null);
  const bookBodyRef = useRef<HTMLDivElement | null>(null);
  // Phones: the folio scrolls as one page; a new verse starts at its top
  const folioRef = useRef<HTMLElement | null>(null);
  const swipeStart = useRef<{ x: number; y: number } | null>(null);
  const [coverImageFailed, setCoverImageFailed] = useState(false);
  // Page-turn leaf for Previous / Next (desktop only, via CSS); n restarts the animation
  const [pageTurn, setPageTurn] = useState<{ dir: 'next' | 'prev'; n: number } | null>(null);

  const currentVerse = useMemo(
    () => SHLOKA_DIRECTORY.find((item) => item.chapter === chapter && item.verseNumber === verseNumber),
    [chapter, verseNumber],
  );
  const chapterMeta = CHAPTER_METAS.find((item) => item.chapter === chapter);
  const chapterData: ChapterVerses | undefined = loadedChapters[chapter];
  const chapterFailed = !chapterData && chapterLoadErrorFor === chapter;
  const canonicalText = currentVerse ? chapterData?.text[currentVerse.verseId] : undefined;
  // Speaker lines ("अर्जुन उवाच") become a small label above the verse, whether stored on their own line or glued on
  const sanskritParts = splitSanskritSpeaker(canonicalText?.sanskrit);
  const iastParts = splitIastSpeaker(canonicalText?.transliteration);
  const displaySanskrit = sanskritParts.text;
  const speakerLabel = sanskritParts.speaker;
  const verseTranslations = chapterData && currentVerse ? chapterData.translations[currentVerse.verseId] ?? [] : [];
  const selectedTranslation = verseTranslations.find((entry) => entry.author === selectedTranslationAuthor)
    ?? verseTranslations[0];

  useEffect(() => {
    let active = true;
    loadChapterVerses(chapter)
      .then((data) => {
        if (!active) return;
        setChapterLoadErrorFor(null);
        setLoadedChapters((prev) => (prev[chapter] === data ? prev : { ...prev, [chapter]: data }));
      })
      .catch(() => {
        if (active) setChapterLoadErrorFor(chapter);
      });
    return () => { active = false; };
  }, [chapter, retryCount]);
  // Glued verses (no line breaks) get one line per danda
  const sanskritText = displaySanskrit.trim();
  const sanskritLines = (sanskritText.includes('\n')
    ? sanskritText.split(/\r?\n/)
    : sanskritText.replace(/([।॥])/gu, '$1\n').split(/\r?\n/)
  ).map((line) => line.trim()).filter(Boolean);
  const hasDoubleDanda = /॥\s*$/u.test(displaySanskrit);
  const chapterVerses = useMemo(
    () => SHLOKA_DIRECTORY.filter((item) => item.chapter === chapter),
    [chapter],
  );

  useEffect(() => {
    continuousRef.current = continuous;
  }, [continuous]);

  useEffect(() => {
    currentIdRef.current = `${chapter}.${verseNumber}`;
  }, [chapter, verseNumber]);

  useEffect(() => {
    if (isContentsOpen) activeChapterItemRef.current?.scrollIntoView({ block: 'nearest' });
  }, [chapter, isContentsOpen]);

  useEffect(() => () => {
    if (audioRef.current) {
      audioRef.current.pause();
      onClipPlayEndOrPause(audioRef.current);
    }
  }, []);

  const selectVerse = (chapterNumber: number, number: number) => {
    setChapter(chapterNumber);
    setVerseNumber(number);
    setSearch('');
  };

  const jumpToSearch = () => {
    const match = getVerseParts(search.trim().replace(/^bg\s*/i, ''));
    if (!match) return;
    const target = SHLOKA_DIRECTORY.find((item) => item.chapter === match.chapter && item.verseNumber === match.verse);
    if (target) selectVerse(match.chapter, match.verse);
  };

  const playVerse = (chapterNumber: number, number: number) => {
    const item = SHLOKA_DIRECTORY.find((entry) => entry.chapter === chapterNumber && entry.verseNumber === number);
    if (!item) return;
    if (!audioRef.current) {
      const audio = new Audio();
      audio.onplay = () => {
        setIsPlaying(true);
        setCurrentPlayingId(currentIdRef.current);
        onClipPlayStart(audio);
      };
      audio.onpause = () => {
        setIsPlaying(false);
        setCurrentPlayingId(null);
        onClipPlayEndOrPause(audio);
      };
      audio.onerror = () => {
        setIsPlaying(false);
        setCurrentPlayingId(null);
        onClipPlayEndOrPause(audio);
      };
      audio.onended = () => {
        setIsPlaying(false);
        setCurrentPlayingId(null);
        onClipPlayEndOrPause(audio);
        if (!continuousRef.current) return;
        const index = SHLOKA_DIRECTORY.findIndex((verse) => verse.verseId === currentIdRef.current);
        const next = SHLOKA_DIRECTORY[index + 1];
        if (next) {
          selectVerse(next.chapter, next.verseNumber);
          window.setTimeout(() => playVerse(next.chapter, next.verseNumber), 0);
        }
      };
      audioRef.current = audio;
    }

    const audio = audioRef.current;
    const targetId = item.verseId;
    if (currentIdRef.current === targetId && !audio.paused) {
      audio.pause();
      return;
    }
    selectVerse(chapterNumber, number);
    currentIdRef.current = targetId;
    audio.src = item.audio_url;
    audio.currentTime = 0;
    audio.play().catch(() => {
      setIsPlaying(false);
      onClipPlayEndOrPause(audio);
    });
  };

  const changeVerse = useCallback((delta: number) => {
    const index = SHLOKA_DIRECTORY.findIndex((item) => item.chapter === chapter && item.verseNumber === verseNumber);
    const next = SHLOKA_DIRECTORY[index + delta];
    if (!next) return;
    setPageTurn((turn) => ({ dir: delta > 0 ? 'next' : 'prev', n: (turn?.n ?? 0) + 1 }));
    selectVerse(next.chapter, next.verseNumber);
  }, [chapter, verseNumber]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.closest('input, select, textarea, [contenteditable="true"]')) return;
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        changeVerse(-1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        changeVerse(1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [changeVerse]);

  const verseIndex = SHLOKA_DIRECTORY.findIndex((item) => item.chapter === chapter && item.verseNumber === verseNumber);
  const firstId = SHLOKA_DIRECTORY[0]?.verseId;
  const lastId = SHLOKA_DIRECTORY[SHLOKA_DIRECTORY.length - 1]?.verseId;
  const isAtStart = currentVerse?.verseId === firstId;
  const isAtEnd = currentVerse?.verseId === lastId;
  const isCurrentPlaying = isPlaying && currentVerse?.verseId === currentPlayingId;
  const openBook = () => {
    setHasBookTransitioned(true);
    setIsBookOpen(true);
  };
  useEffect(() => {
    folioRef.current?.scrollTo({ top: 0 });
  }, [chapter, verseNumber]);

  // Touch swipe on the book: left = next verse, right = previous (a mostly horizontal swipe of 60px+)
  const onSwipeStart = (event: ReactTouchEvent) => {
    const t = event.touches[0];
    swipeStart.current = { x: t.clientX, y: t.clientY };
  };
  const onSwipeEnd = (event: ReactTouchEvent) => {
    const start = swipeStart.current;
    swipeStart.current = null;
    const t = event.changedTouches[0];
    if (!start || !t) return;
    const dx = t.clientX - start.x;
    const dy = t.clientY - start.y;
    if (Math.abs(dx) >= 60 && Math.abs(dx) > Math.abs(dy) * 2) changeVerse(dx < 0 ? 1 : -1);
  };

  const closeBook = () => {
    setIsContentsOpen(false);
    setHasBookTransitioned(true);
    setIsBookOpen(false);
  };
  // Closed book follows the mouse a little (CSS variables, no re-render); off for touch and reduced motion
  const tiltFrame = useRef(0);
  const tiltBook = (event: ReactPointerEvent<HTMLDivElement>) => {
    const body = bookBodyRef.current;
    if (!body || event.pointerType !== 'mouse' || tiltFrame.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const box = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;
    tiltFrame.current = requestAnimationFrame(() => {
      tiltFrame.current = 0;
      body.style.setProperty('--ry', `${(x * 14).toFixed(2)}deg`);
      body.style.setProperty('--rx', `${(-y * 8).toFixed(2)}deg`);
    });
  };
  const resetTilt = () => {
    bookBodyRef.current?.style.removeProperty('--ry');
    bookBodyRef.current?.style.removeProperty('--rx');
  };

  return (
    <main className="gita-book-reader mx-auto flex w-full max-w-[1180px] flex-1 min-h-0 flex-col overflow-hidden px-3 py-3 sm:px-6 lg:px-8">
      <div className={`gita-book-scene ${isBookOpen ? 'is-open' : 'is-closed'} ${hasBookTransitioned ? 'has-transition' : ''}`}>
        <section className="gita-front-cover-stage" aria-label="Bhagavad Gita book cover" aria-hidden={isBookOpen}>
          <div className="gita-book3d" onPointerMove={tiltBook} onPointerLeave={resetTilt}>
            <div className="gita-book3d-body" ref={bookBodyRef}>
              <div aria-hidden="true" className="gita-book3d-face gita-book3d-back" />
              <div aria-hidden="true" className="gita-book3d-face gita-book3d-spine" />
              <div aria-hidden="true" className="gita-book3d-face gita-book3d-edge gita-book3d-edge-right" />
              <div aria-hidden="true" className="gita-book3d-face gita-book3d-edge gita-book3d-edge-top" />
              <div aria-hidden="true" className="gita-book3d-face gita-book3d-edge gita-book3d-edge-bottom" />
              <div aria-hidden="true" className="gita-book3d-firstpage">
                <span className="gita-book3d-om font-sanskrit" lang="sa">ॐ</span>
                <p className="font-sanskrit" lang="sa">श्रीमद्भगवद्गीता</p>
                <i />
                <p className="font-cinzel">Chapter {chapter}{chapterMeta ? ` · ${chapterMeta.englishTitle}` : ''}</p>
              </div>
              <div className="gita-book3d-lid">
                <div className="gita-front-cover">
                  <header className="gita-cover-header">
                    <span className="gita-cover-inscription font-sanskrit" lang="sa">ॐ श्रीपरमात्मने नमः</span>
                    <p className="gita-cover-devanagari font-sanskrit" lang="sa">श्रीमद्भगवद्गीता</p>
                    <p className="gita-cover-roman font-cinzel">ŚRĪMAD BHAGAVAD GĪTĀ</p>
                  </header>
                  <div className="gita-cover-art-frame">
                    {coverImageFailed
                      ? <BookCoverArt />
                      : <img src="/bookcover.jpg" alt="Krishna and Arjuna on the chariot at Kurukshetra" decoding="async" onError={() => setCoverImageFailed(true)} />}
                  </div>
                  <p className="gita-cover-subtitle">The Song of the Divine</p>
                </div>
                <div aria-hidden="true" className="gita-cover-inside" />
              </div>
            </div>
          </div>
          <div className="gita-book3d-actions">
            <button onClick={openBook} className="gita-cover-open-button"><BookOpen className="h-5 w-5" /><span>Open Scripture</span><span className="font-sanskrit" lang="sa">ग्रन्थ उद्घाटयत</span></button>
            <button onClick={onBack} className="gita-cover-back-button"><ArrowLeft className="h-3.5 w-3.5" /><span>Return to Sanctuary / Chat</span></button>
          </div>
        </section>

        <div className="gita-book-pages-view" aria-hidden={!isBookOpen}>
      <header className="gita-book-toolbar royal-card mb-3 flex shrink-0 flex-wrap items-center justify-between gap-2 rounded-2xl border border-[#C5A059]/30 px-3 py-2.5 shadow-sm sm:px-4">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3 max-md:hidden">
          <button onClick={onBack} aria-label="Return to Sanctuary / Chat" className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-[#C5A059]/40 bg-white/75 px-2.5 py-2 text-xs font-semibold text-[#704B20] hover:bg-[#FFFDF8] sm:px-3 sm:text-sm">
            <ArrowLeft className="h-4 w-4" /><span className="hidden sm:inline">Return to Sanctuary / Chat</span><span className="hidden min-[481px]:inline sm:hidden">Back to chat</span>
          </button>
          <div className="min-w-0 border-l border-[#C5A059]/30 pl-2 sm:pl-3">
            <p className="font-sanskrit text-sm font-semibold leading-tight text-[#8C2D19]" lang="sa">श्रीमद्भगवद्गीता</p>
            <h1 className="truncate font-cinzel text-xs font-bold tracking-wide text-[#4B3825] sm:text-sm">The Sacred Book</h1>
          </div>
          <button onClick={closeBook} title="Close Book / View Cover" aria-label="Close Book / View Cover" className="gita-cover-return-button"><span className="max-[480px]:hidden">Close Book / View Cover</span><span aria-hidden="true" className="min-[481px]:hidden">Cover</span></button>
        </div>
        {/* Phones: one compact row (back, contents, chapter, search, cover); every target is 44px */}
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap">
          <button onClick={onBack} aria-label="Return to chat" className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#C5A059]/40 bg-white/75 text-[#704B20] hover:bg-[#FFFDF8] md:hidden">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          </button>
          <button onClick={() => setIsContentsOpen(true)} aria-expanded={isContentsOpen} aria-label="Contents" className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-[#C5A059]/35 bg-white/75 px-3 py-2 text-xs font-semibold text-[#704B20] hover:bg-[#FFFDF8] max-md:h-11 max-md:w-11 max-md:justify-center max-md:px-0">
            <List className="h-4 w-4 text-[#A27427]" aria-hidden="true" /><span className="max-md:hidden">Contents</span>
          </button>
          <label className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-[#C5A059]/35 bg-white/75 px-3 py-2 text-xs text-[#6A5A48] max-md:h-11 sm:min-w-[230px] sm:flex-none">
            <BookOpen className="h-4 w-4 shrink-0 text-[#A27427] max-md:hidden" />
            <span className="shrink-0 max-md:sr-only">Chapter</span>
            <select value={chapter} onChange={(event) => selectVerse(Number(event.target.value), 1)} title={chapterMeta ? `Chapter ${chapterMeta.chapter} · ${chapterMeta.englishTitle}` : undefined} className="min-w-0 flex-1 bg-transparent font-semibold text-[#704B20] outline-none">
              {CHAPTER_METAS.map((meta) => <option key={meta.chapter} value={meta.chapter}>{meta.chapter} · {meta.englishTitle}</option>)}
            </select>
          </label>
          <button type="button" onClick={() => setIsSearchOpen((open) => !open)} aria-expanded={isSearchOpen} aria-label="Find a verse" className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border text-[#704B20] md:hidden ${isSearchOpen ? 'border-[#A27427] bg-[#F1E0BB]' : 'border-[#C5A059]/35 bg-white/75'}`}>
            <Search className="h-4 w-4" aria-hidden="true" />
          </button>
          <button onClick={closeBook} aria-label="Close Book / View Cover" className="gita-cover-return-button h-11 md:hidden">Cover</button>
          <form className={`flex min-w-0 flex-1 rounded-xl border border-[#C5A059]/35 bg-white/75 max-md:h-11 max-md:basis-full sm:flex-none ${isSearchOpen ? '' : 'max-md:hidden'}`} onSubmit={(event) => { event.preventDefault(); jumpToSearch(); setIsSearchOpen(false); }}>
            <label className="flex min-w-0 flex-1 items-center gap-2 px-3 sm:flex-none">
              <Search className="h-4 w-4 shrink-0 text-[#A27427]" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find verse, e.g. 2.47" aria-label="Find verse" inputMode="decimal" className="w-full min-w-0 bg-transparent py-2 text-base text-[#2C261F] outline-none placeholder:text-[#8C7B68] sm:w-36 md:text-sm" />
            </label>
            <button type="submit" className="rounded-r-xl border-l border-[#C5A059]/30 px-3 text-xs font-semibold text-[#8C2D19] hover:bg-[#F4ECE1]">Go</button>
          </form>
        </div>
      </header>

      <section ref={folioRef} onTouchStart={onSwipeStart} onTouchEnd={onSwipeEnd} className="gita-book-cover min-h-0 flex-1 rounded-[1.35rem] p-[7px] sm:p-3" aria-label="Sacred book folio">
        <div className="gita-book-spread">
          {pageTurn && <div key={pageTurn.n} aria-hidden="true" className={`gita-page-leaf is-${pageTurn.dir}`} onAnimationEnd={() => setPageTurn(null)} />}
          {currentVerse && chapterMeta ? <>
            <section className="gita-book-page gita-book-left-page" aria-label="Sanskrit shloka">
              <header className="gita-page-running-head">
                <span>Chapter {chapter}</span><span className="font-sanskrit" lang="sa">{sanskritChapterTitles[chapter - 1]}</span><span className="gita-running-title">{chapterMeta.englishTitle}</span>
              </header>
              <div key={currentVerse.verseId} className="gita-page-scroll gita-sanskrit-content gita-verse-enter">
                <div aria-hidden="true" className="gita-page-ornament"><span>✦</span><i /><span>❧</span><i /><span>✦</span></div>
                {canonicalText ? <>
                  {speakerLabel && <p className="gita-speaker-label font-sanskrit" lang="sa">{speakerLabel}</p>}
                  <div className="gita-sanskrit-lines" lang="sa">
                    {sanskritLines.map((line, index) => <p key={`${index}-${line}`} className="font-sanskrit" style={{ '--line': index } as CSSProperties}>{line}</p>)}
                    {!hasDoubleDanda && <p className="gita-verse-end font-sanskrit">{chapter}.{verseNumber}</p>}
                  </div>
                  {iastParts.text && <div className="gita-transliteration">
                    {iastParts.speaker && <span className="gita-transliteration-speaker">{iastParts.speaker}</span>}
                    <span>{iastParts.text}</span>
                  </div>}
                </> : chapterFailed ? <div className="gita-translation-status" role="alert">
                  The verse text could not be loaded.{' '}
                  <button type="button" className="gita-retry-link" onClick={() => setRetryCount((n) => n + 1)}>Try again</button>
                </div> : <p className="gita-translation-status" role="status">Loading the verse…</p>}
              </div>
              <footer className="gita-page-number gita-page-number-left">{chapter}.{verseNumber}</footer>
            </section>

            <section className="gita-book-page gita-book-right-page" aria-label="English meaning and recitation">
              <article key={currentVerse.verseId} className="gita-page-turn">
                <header className="gita-page-running-head gita-right-running-head"><span>Bhagavad Gita</span><span>English meaning</span></header>
                <div className="gita-page-scroll gita-meaning-content">
                  <div className="gita-translation-heading-row">
                    <h2 className="gita-meaning-heading">English meaning</h2>
                    <span className="gita-translation-info" title="Translations as given in the project dataset; wording may differ from the published editions." aria-label="Translations as given in the project dataset; wording may differ from the published editions.">i</span>
                  </div>
                  {verseTranslations.length > 1 && <label className="gita-translation-picker">Translation by
                    <select value={selectedTranslation?.author ?? ''} onChange={(event) => setSelectedTranslationAuthor(event.target.value)}>
                      {verseTranslations.map((entry) => <option key={entry.author} value={entry.author}>{entry.author}</option>)}
                    </select>
                  </label>}
                  {selectedTranslation && <>
                    <p className="gita-translation">{selectedTranslation.text}</p>
                    <p className="gita-translation-author">Translation: {selectedTranslation.author}</p>
                  </>}
                  {!selectedTranslation && !chapterData && !chapterFailed && <p className="gita-translation-status">Loading translations…</p>}
                  {!selectedTranslation && chapterFailed && <p className="gita-translation-status">Translations could not be loaded.</p>}
                  {!selectedTranslation && chapterData && <p className="gita-translation-status">No English translation available for this verse.</p>}
                  <section className="gita-recitation-plate" aria-label="Verse recitation">
                    <div className="gita-recitation-copy"><span className="gita-recitation-icon"><Volume2 className="h-5 w-5" /></span><div><h3>Sacred recitation</h3><p>BG {currentVerse.verseId} · authentic verse audio</p></div></div>
                    <div className="gita-recitation-actions">
                      <label><input type="checkbox" checked={continuous} onChange={(event) => setContinuous(event.target.checked)} /> Continuous</label>
                      <button onClick={() => playVerse(chapter, verseNumber)} aria-label={isCurrentPlaying ? 'Pause recitation' : 'Play recitation'}>
                        {isCurrentPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}{isCurrentPlaying ? 'Pause' : 'Play verse'}
                      </button>
                    </div>
                  </section>
                </div>
                <footer className="gita-page-number gita-page-number-right">{chapter}.{verseNumber}</footer>
              </article>
              <div aria-hidden="true" className="gita-bookmark" />
            </section>
          </> : <p className="py-20 text-center text-[#6A5A48]">This verse is not available in the scripture directory.</p>}
        </div>
      </section>

      <footer className="gita-book-navigation flex shrink-0 items-center justify-between gap-2 pt-2.5">
        <button onClick={() => changeVerse(-1)} disabled={isAtStart} aria-label="Previous verse" className="inline-flex items-center gap-1 rounded-xl border border-[#C5A059]/40 bg-[#FFFDF8] px-3 py-2 text-xs font-semibold text-[#704B20] shadow-sm hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 max-md:h-11 sm:px-4 sm:text-sm"><ChevronLeft className="h-4 w-4" aria-hidden="true" /><span className="max-md:hidden">Previous Verse</span><span className="md:hidden">Prev</span></button>
        <span className="text-center font-cinzel text-[10px] font-semibold text-[#6A5A48] max-md:hidden sm:text-xs">Verse {Math.max(verseIndex + 1, 1)} of {SHLOKA_DIRECTORY.length}</span>
        {/* Phones: the recitation is always one tap away, not at the end of the English page */}
        {/* The wrapper carries md:hidden: .vyom-play-button's own display (unlayered CSS) beats Tailwind's */}
        {currentVerse && (
          <div className="md:hidden">
            <button onClick={() => playVerse(chapter, verseNumber)} aria-label={isCurrentPlaying ? `Pause recitation of BG ${currentVerse.verseId}` : `Play recitation of BG ${currentVerse.verseId}`} className="vyom-play-button h-11 min-w-0 justify-center">
              {isCurrentPlaying ? <Pause className="h-4 w-4" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}
              <span>{isCurrentPlaying ? 'Pause' : 'Play'} {currentVerse.verseId}</span>
            </button>
          </div>
        )}
        <button onClick={() => changeVerse(1)} disabled={isAtEnd} aria-label="Next verse" className="inline-flex items-center gap-1 rounded-xl border border-[#C5A059]/40 bg-[#FFFDF8] px-3 py-2 text-xs font-semibold text-[#704B20] shadow-sm hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 max-md:h-11 sm:px-4 sm:text-sm"><span className="max-md:hidden">Next Verse</span><span className="md:hidden">Next</span><ChevronRight className="h-4 w-4" aria-hidden="true" /></button>
      </footer>
        </div>
      </div>

      {isContentsOpen && <div className="gita-contents-layer" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setIsContentsOpen(false); }}>
        <aside className="gita-contents-drawer" role="dialog" aria-modal="true" aria-label="Gita contents">
          <header><div><p>Contents</p><span>18 chapters · 701 shlokas</span></div><button onClick={() => setIsContentsOpen(false)} aria-label="Close contents"><X className="h-5 w-5" /></button></header>
          <nav aria-label="Gita chapters" className="gita-contents-list">
            {CHAPTER_METAS.map((meta) => {
              const isActive = chapter === meta.chapter;
              return <div key={meta.chapter} ref={isActive ? activeChapterItemRef : null} className="gita-chapter-group">
                <button onClick={() => selectVerse(meta.chapter, 1)} aria-current={isActive ? 'true' : undefined} className={`gita-chapter-choice ${isActive ? 'is-active' : ''}`}>
                  <span className="gita-chapter-name">{String(meta.chapter).padStart(2, '0')} · {meta.englishTitle}</span><span className="font-sanskrit" lang="sa">{sanskritChapterTitles[meta.chapter - 1]}</span>
                </button>
                {isActive && <div className="gita-verse-grid">{chapterVerses.map((item) => <button key={item.verseId} onClick={() => { selectVerse(item.chapter, item.verseNumber); setIsContentsOpen(false); }} aria-label={`Verse ${item.verseNumber}`} aria-current={item.verseNumber === verseNumber ? 'true' : undefined} className={item.verseNumber === verseNumber ? 'is-active' : ''}>{item.verseNumber}</button>)}</div>}
              </div>;
            })}
          </nav>
        </aside>
      </div>}
    </main>
  );
}
