/**
 * A verse as the verse modal and quote card show it. Every field comes from the canonical data
 * (backend/data/processed/verses.jsonl, via data/verseStore.ts).
 *
 * This file used to hold 10 hand-written entries (2.47, 18.66, 2.20, 4.7, 4.8, 6.5, 6.35, 9.22, 11.32,
 * 18.78) with their own Sanskrit, transliteration, translation, author credit, theme and commentary
 * note. Their translation/author pairs did not match the dataset and the notes had no recorded
 * source, so they were removed on 2026-11-19 (backup: gitaVerses.ts.bak1).
 */
export interface GitaVerse {
  verse_id: string; // e.g. "2.47"
  chapter: number;
  verse: number;
  sanskrit: string;
  transliteration: string;
  word_meanings: string;
  /** First translation in public/translations/chNN.json (the export's preferred author) */
  translation: string;
  author: string;
}
