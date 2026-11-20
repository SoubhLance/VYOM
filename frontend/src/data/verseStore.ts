import type { GitaVerse } from './gitaVerses';

/**
 * Verse text for all 701 verses, used by the chat, the verse modal, the quote card and the Sacred Book.
 * Both files are generated from the canonical backend/data/processed/verses.jsonl (never hand-edit):
 *   /verses/chNN.json        sanskrit, transliteration, word meanings (scripts/export_verses.py)
 *   /translations/chNN.json  English translations, preferred author first (scripts/export_translations.py)
 * shlokaDirectory.json is used only for its audio clip mapping, never for text.
 */

/** Verses per chapter in verses.jsonl (701 in total; chapter 13 has 35). */
export const VERSE_COUNTS = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78] as const;

/** "BG 2.47", "2:47" or "2.47" -> "2.47"; null when it is not a real verse. */
export function normalizeVerseId(ref: string): string | null {
  const m = ref.trim().match(/^(?:BG|Gita|Verse)?\s*(\d{1,2})\s*[.:]\s*(\d{1,2})$/i);
  if (!m) return null;
  const chapter = Number(m[1]);
  const verse = Number(m[2]);
  if (chapter < 1 || chapter > 18 || verse < 1 || verse > VERSE_COUNTS[chapter - 1]) return null;
  return `${chapter}.${verse}`;
}

export interface VerseTranslation { author: string; text: string }
export interface VerseText {
  sanskrit: string;
  transliteration: string;
  word_meanings: string;
  /** english[0] in verses.jsonl: the translation the LLM prompt shows and the quote verifier checks */
  translation?: VerseTranslation;
}
export interface ChapterVerses {
  text: Record<string, VerseText>;
  translations: Record<string, VerseTranslation[]>;
}

const chapterCache = new Map<number, Promise<ChapterVerses>>();

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

/** Text and translations of one chapter, fetched once and cached. Rejects if either file fails. */
export function loadChapterVerses(chapter: number): Promise<ChapterVerses> {
  let pending = chapterCache.get(chapter);
  if (!pending) {
    const nn = String(chapter).padStart(2, '0');
    pending = Promise.all([
      fetchJson<Record<string, VerseText>>(`/verses/ch${nn}.json`),
      fetchJson<Record<string, VerseTranslation[]>>(`/translations/ch${nn}.json`),
    ]).then(([text, translations]) => ({ text, translations }));
    // A failed fetch must not stay cached, so the next attempt can try again
    pending.catch(() => chapterCache.delete(chapter));
    chapterCache.set(chapter, pending);
  }
  return pending;
}

/** Full verse for the detail modal and quote card. Rejects if the files can't be fetched. */
export async function loadVerse(ref: string): Promise<GitaVerse | null> {
  const id = normalizeVerseId(ref);
  if (!id) return null;
  const [chapter, verse] = id.split('.').map(Number);
  const { text, translations } = await loadChapterVerses(chapter);
  const t = text[id];
  if (!t) return null;
  // Same translator as the answer's quotes; any other only if that one is missing
  const translation = t.translation?.text.trim() ? t.translation : (translations[id] ?? []).find((entry) => entry.text.trim());
  return {
    verse_id: id,
    chapter,
    verse,
    sanskrit: t.sanskrit,
    transliteration: t.transliteration,
    word_meanings: t.word_meanings,
    translation: translation?.text ?? '',
    author: translation?.author ?? '',
  };
}
