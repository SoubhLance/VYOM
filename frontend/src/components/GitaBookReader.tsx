import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from 'react';
import { ArrowLeft, BookOpen, ChevronLeft, ChevronRight, List, Pause, Play, Search, Volume2, X } from 'lucide-react';
import { GITA_VERSES } from '../data/gitaVerses';
import { CHAPTER_METAS, SHLOKA_DIRECTORY } from '../data/recitationIndex';
import { onClipPlayEndOrPause, onClipPlayStart } from '../services/audioCoordinator';
import { BookCoverArt } from './BookCoverArt';
import './GitaBookReader.css';

interface GitaBookReaderProps {
  onBack: () => void;
  initialVerseId?: string | null;
}

interface VerseTranslation {
  author: string;
  text: string;
}

type ChapterTranslationMap = Record<string, VerseTranslation[]>;

const chapterTranslationCache = new Map<number, ChapterTranslationMap>();

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
  const [continuous, setContinuous] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentPlayingId, setCurrentPlayingId] = useState<string | null>(null);
  const [isContentsOpen, setIsContentsOpen] = useState(false);
  // Opened at a specific verse: start on the open pages (the cover is one click away)
  const [isBookOpen, setIsBookOpen] = useState(initialVerse !== null);
  const [hasBookTransitioned, setHasBookTransitioned] = useState(false);
  const [chapterTranslations, setChapterTranslations] = useState<ChapterTranslationMap>({});
  const [translationsLoadedFor, setTranslationsLoadedFor] = useState<number | null>(null);
  const [translationLoadErrorFor, setTranslationLoadErrorFor] = useState<number | null>(null);
  const [selectedTranslationAuthor, setSelectedTranslationAuthor] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const continuousRef = useRef(continuous);
  const currentIdRef = useRef(initialVerse ? `${initialVerse.chapter}.${initialVerse.verse}` : '1.1');
  const activeChapterItemRef = useRef<HTMLDivElement | null>(null);
  const bookBodyRef = useRef<HTMLDivElement | null>(null);
  const [coverImageFailed, setCoverImageFailed] = useState(false);
  // Page-turn leaf for Previous / Next (desktop only, via CSS); n restarts the animation
  const [pageTurn, setPageTurn] = useState<{ dir: 'next' | 'prev'; n: number } | null>(null);

  const currentVerse = useMemo(
    () => SHLOKA_DIRECTORY.find((item) => item.chapter === chapter && item.verseNumber === verseNumber),
    [chapter, verseNumber],
  );
  const chapterMeta = CHAPTER_METAS.find((item) => item.chapter === chapter);
  const legacyVerse = currentVerse ? GITA_VERSES[currentVerse.verseId] : undefined;
  const displaySanskrit = legacyVerse?.sanskrit ?? currentVerse?.sanskrit ?? '';
  const displayTransliteration = legacyVerse?.transliteration ?? currentVerse?.transliteration ?? '';
  const activeChapterTranslations = translationsLoadedFor === chapter
    ? chapterTranslations
    : chapterTranslationCache.get(chapter);
  const translationsAreLoaded = activeChapterTranslations !== undefined;
  const verseTranslations = translationsAreLoaded
    ? activeChapterTranslations?.[currentVerse?.verseId ?? ''] ?? []
    : [];
  const selectedTranslation = verseTranslations.find((entry) => entry.author === selectedTranslationAuthor)
    ?? verseTranslations[0];

  useEffect(() => {
    let active = true;
    const cached = chapterTranslationCache.get(chapter);
    if (cached) {
      return () => { active = false; };
    }

    fetch(`/translations/ch${String(chapter).padStart(2, '0')}.json`)
      .then((response) => {
        if (!response.ok) throw new Error('Unable to load chapter translations.');
        return response.json() as Promise<ChapterTranslationMap>;
      })
      .then((data) => {
        chapterTranslationCache.set(chapter, data);
        if (active) {
          setChapterTranslations(data);
          setTranslationsLoadedFor(chapter);
          setTranslationLoadErrorFor(null);
        }
      })
      .catch(() => {
        if (active) {
          setChapterTranslations({});
          setTranslationsLoadedFor(chapter);
          setTranslationLoadErrorFor(chapter);
        }
      });
    return () => { active = false; };
  }, [chapter]);
  const rawSanskritLines = useMemo(() => {
    const text = displaySanskrit.trim();
    if (!text) return [];
    const lines = text.includes('\n')
      ? text.split(/\r?\n/)
      : /[।॥]/u.test(text)
        ? text.replace(/([।॥])/gu, '$1\n').split(/\r?\n/)
        : [text];
    return lines.map((line) => line.trim()).filter(Boolean);
  }, [displaySanskrit]);
  const speakerLabel = ['श्रीभगवानुवाच', 'शरभगवनवच'].includes(rawSanskritLines[0] ?? '')
    ? rawSanskritLines[0]
    : '';
  const sanskritLines = speakerLabel ? rawSanskritLines.slice(1) : rawSanskritLines;
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
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <button onClick={onBack} aria-label="Return to Sanctuary / Chat" className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-[#C5A059]/40 bg-white/75 px-2.5 py-2 text-xs font-semibold text-[#704B20] hover:bg-[#FFFDF8] sm:px-3 sm:text-sm">
            <ArrowLeft className="h-4 w-4" /><span className="hidden sm:inline">Return to Sanctuary / Chat</span><span className="hidden min-[481px]:inline sm:hidden">Back to chat</span>
          </button>
          <div className="min-w-0 border-l border-[#C5A059]/30 pl-2 sm:pl-3">
            <p className="font-sanskrit text-sm font-semibold leading-tight text-[#8C2D19]" lang="sa">श्रीमद्भगवद्गीता</p>
            <h1 className="truncate font-cinzel text-xs font-bold tracking-wide text-[#4B3825] sm:text-sm">The Sacred Book</h1>
          </div>
          <button onClick={closeBook} title="Close Book / View Cover" aria-label="Close Book / View Cover" className="gita-cover-return-button"><span className="max-[480px]:hidden">Close Book / View Cover</span><span aria-hidden="true" className="min-[481px]:hidden">Cover</span></button>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap">
          <button onClick={() => setIsContentsOpen(true)} aria-expanded={isContentsOpen} className="inline-flex items-center gap-1.5 rounded-xl border border-[#C5A059]/35 bg-white/75 px-3 py-2 text-xs font-semibold text-[#704B20] hover:bg-[#FFFDF8]">
            <List className="h-4 w-4 text-[#A27427]" /> Contents
          </button>
          <label className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-[#C5A059]/35 bg-white/75 px-3 py-2 text-xs text-[#6A5A48] sm:min-w-[230px] sm:flex-none">
            <BookOpen className="h-4 w-4 shrink-0 text-[#A27427]" />
            <span className="shrink-0 max-[480px]:sr-only">Chapter</span>
            <select value={chapter} onChange={(event) => selectVerse(Number(event.target.value), 1)} title={chapterMeta ? `Chapter ${chapterMeta.chapter} · ${chapterMeta.englishTitle}` : undefined} className="min-w-0 flex-1 bg-transparent font-semibold text-[#704B20] outline-none">
              {CHAPTER_METAS.map((meta) => <option key={meta.chapter} value={meta.chapter}>{meta.chapter} · {meta.englishTitle}</option>)}
            </select>
          </label>
          <form className="flex min-w-0 flex-1 rounded-xl border border-[#C5A059]/35 bg-white/75 max-[480px]:basis-full sm:flex-none" onSubmit={(event) => { event.preventDefault(); jumpToSearch(); }}>
            <label className="flex min-w-0 flex-1 items-center gap-2 px-3 sm:flex-none">
              <Search className="h-4 w-4 shrink-0 text-[#A27427]" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find verse, e.g. 2.47" aria-label="Find verse" className="w-full min-w-0 bg-transparent py-2 text-sm text-[#2C261F] outline-none placeholder:text-[#8C7B68] sm:w-36" />
            </label>
            <button type="submit" className="rounded-r-xl border-l border-[#C5A059]/30 px-3 text-xs font-semibold text-[#8C2D19] hover:bg-[#F4ECE1]">Go</button>
          </form>
        </div>
      </header>

      <section className="gita-book-cover min-h-0 flex-1 rounded-[1.35rem] p-[7px] sm:p-3" aria-label="Sacred book folio">
        <div className="gita-book-spread">
          {pageTurn && <div key={pageTurn.n} aria-hidden="true" className={`gita-page-leaf is-${pageTurn.dir}`} onAnimationEnd={() => setPageTurn(null)} />}
          {currentVerse && chapterMeta ? <>
            <section className="gita-book-page gita-book-left-page" aria-label="Sanskrit shloka">
              <header className="gita-page-running-head">
                <span>Chapter {chapter}</span><span className="font-sanskrit" lang="sa">{sanskritChapterTitles[chapter - 1]}</span><span className="gita-running-title">{chapterMeta.englishTitle}</span>
              </header>
              <div key={currentVerse.verseId} className="gita-page-scroll gita-sanskrit-content gita-verse-enter">
                <div aria-hidden="true" className="gita-page-ornament"><span>✦</span><i /><span>❧</span><i /><span>✦</span></div>
                {speakerLabel && <p className="gita-speaker-label font-sanskrit" lang="sa">{speakerLabel}</p>}
                <div className="gita-sanskrit-lines" lang="sa">
                  {sanskritLines.map((line, index) => <p key={`${index}-${line}`} className="font-sanskrit" style={{ '--line': index } as CSSProperties}>{line}</p>)}
                  {!hasDoubleDanda && <p className="gita-verse-end font-sanskrit">{chapter}.{verseNumber}</p>}
                </div>
                {displayTransliteration && <p className="gita-transliteration">{displayTransliteration}</p>}
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
                  {!selectedTranslation && !translationsAreLoaded && translationLoadErrorFor !== chapter && <p className="gita-translation-status">Loading translations…</p>}
                  {!selectedTranslation && translationsAreLoaded && translationLoadErrorFor === chapter && <p className="gita-translation-status">Translations could not be loaded.</p>}
                  {!selectedTranslation && translationsAreLoaded && translationLoadErrorFor !== chapter && <p className="gita-translation-status">No English translation available for this verse.</p>}
                  {legacyVerse && <aside className="gita-reflection"><h3>Commentary note · {legacyVerse.author}</h3><p>{legacyVerse.commentary_summary}</p></aside>}
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
        <button onClick={() => changeVerse(-1)} disabled={isAtStart} className="inline-flex items-center gap-1 rounded-xl border border-[#C5A059]/40 bg-[#FFFDF8] px-3 py-2 text-xs font-semibold text-[#704B20] shadow-sm hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 sm:px-4 sm:text-sm"><ChevronLeft className="h-4 w-4" /> Previous Verse</button>
        <span className="text-center font-cinzel text-[10px] font-semibold text-[#6A5A48] sm:text-xs">Verse {Math.max(verseIndex + 1, 1)} of {SHLOKA_DIRECTORY.length}</span>
        <button onClick={() => changeVerse(1)} disabled={isAtEnd} className="inline-flex items-center gap-1 rounded-xl border border-[#C5A059]/40 bg-[#FFFDF8] px-3 py-2 text-xs font-semibold text-[#704B20] shadow-sm hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 sm:px-4 sm:text-sm">Next Verse <ChevronRight className="h-4 w-4" /></button>
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
