/**
 * Speaker labels ("अर्जुन उवाच" / "arjuna uvācha") are stored inconsistently in verses.jsonl: on their own
 * line, glued to the verse (12.1 "अर्जुन उवाचएवं…"), or only in the transliteration. Display only: we split
 * them off so every view can show them as one small label line above the verse. The data is not changed.
 *
 * Only the five real speakers match, and only at the very start, so a narrative "उवाच" inside a verse
 * (1.25 "उवाच पार्थ…", 2.10 "तमुवाच…") stays part of the verse.
 */

const SANSKRIT_SPEAKER = /^\s*(श्री\s?भगवानुवाच|(?:अर्जुन|सञ्जय|संजय|धृतराष्ट्र)\s+उवाच)[\s।॥]*/u;
const IAST_SPEAKER = /^\s*((?:śhrī[\s-]?bhagavān|arjuna|sañjaya|dhṛitarāśhṭra|dhṛitarāśhtra)\s+uvācha)[\s,.|]*/iu;

export interface SpeakerSplit {
  /** The label, e.g. "श्री भगवानुवाच" or "śhrī bhagavān uvācha"; null when the verse has none */
  speaker: string | null;
  /** The verse without its label */
  text: string;
}

function split(text: string | undefined, pattern: RegExp): SpeakerSplit {
  const value = (text ?? '').normalize('NFC');
  const match = value.match(pattern);
  if (!match) return { speaker: null, text: value };
  return { speaker: match[1].replace(/\s+/g, ' ').trim(), text: value.slice(match[0].length) };
}

export const splitSanskritSpeaker = (text: string | undefined) => split(text, SANSKRIT_SPEAKER);
export const splitIastSpeaker = (text: string | undefined) => split(text, IAST_SPEAKER);
