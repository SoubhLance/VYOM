import { useEffect, useState } from 'react';
import { loadChapterVerses, normalizeVerseId, type VerseTranslation } from '../../data/verseStore';

/**
 * The English translation under a chat verse card: the same translator the answer's quotes come
 * from (english[0] in verses.jsonl, what the LLM prompt shows and the quote verifier checks).
 * Loads the verse's chapter file once (cached in verseStore); shows nothing if it can't.
 */
export function VerseCardTranslation({ verseId }: { verseId: string }) {
  const id = normalizeVerseId(verseId);
  const [loaded, setLoaded] = useState<{ id: string; translation: VerseTranslation | null } | null>(null);

  useEffect(() => {
    if (!id) return;
    let active = true;
    loadChapterVerses(Number(id.split('.')[0]))
      .then((chapter) => {
        const t = chapter.text[id]?.translation;
        if (active) setLoaded({ id, translation: t?.text.trim() ? t : null });
      })
      .catch(() => {
        if (active) setLoaded({ id, translation: null });
      });
    return () => { active = false; };
  }, [id]);

  const translation = loaded?.id === id ? loaded.translation : null;
  if (!translation) return null;
  return (
    <div className="border-t border-[#C5A059]/15 pt-2">
      <p className="text-[13px] leading-6 text-[#2C261F]">{translation.text}</p>
      <p className="mt-0.5 text-[11px] text-[#6A5A48]">Translation: {translation.author}</p>
    </div>
  );
}
