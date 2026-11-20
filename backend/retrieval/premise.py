"""False-premise guard: never attach a question's premise to a verse that doesn't contain it.

"How does the Gita guide celibacy in the Karthik month?" assumes the Gita says something about
Kartik. If no verse shown to the LLM mentions that term, any answer sentence that names the term
next to a BG citation is pinning the user's premise on a verse:
- the honest "The Gita says nothing about the Kartik month (BG 6.14)." keeps its words, loses the citation;
- any other such sentence is removed (with the usual "unsupported statement" warning).
Only the terms below count as premises (calendar months, festivals, observances), so
ordinary words from a question are never touched. A term that a shown verse does contain
(10.35 names Mārgaśīrṣa among months) is a real reference and is left alone.
"""

import re
import unicodedata
from typing import Any

REMOVED_WARNING = "One unsupported statement was removed from the answer."

# Normalised stems (see _norm). A word matches when its normalised form starts with the stem.
PREMISE_STEMS: dict[str, list[str]] = {
    # Hindu lunar months (several spellings normalise to one stem)
    "hindu month": [
        "caitra", "chaitra", "vaisak", "vaishak", "jyest", "jyesht", "asad", "ashad", "sravan", "shravan",
        "bhadrapad", "asvin", "ashvin", "ashwin", "kartik", "margasir", "margashir", "margshir", "agrahayan",
        "paus", "pusa", "magh", "phalgun", "falgun",
    ],
    # Gregorian months ("may" and "march" are too common as words; left out)
    "month": ["january", "february", "april", "june", "july", "august", "september", "october", "november", "december"],
    "festival": [
        "diwali", "deepavali", "dipavali", "holi", "navarat", "navrat", "dussehr", "dasar", "vijayadas",
        "janmast", "shivarat", "sivarat", "ekadas", "pongal", "sankrant", "onam", "karva", "karwa",
        "rakhi", "rakshabandhan", "ganeshcaturt", "ganeshchaturt", "ramnavam", "christmas", "ramadan", "eid",
    ],
    "observance": ["vrat", "upavas", "chaturmas", "caturmas", "shraddh", "sraddh", "pitrupaksh", "tithi", "muhurt", "panchang"],
    # Modern concepts (phone, internet...) are deliberately absent: applying a verse to the user's modern
    # situation is wanted ("how it applies"), so only the prompt rule covers them, not this filter.
}

_CITATION = re.compile(
    r"\s*\((?:paraphrase\s*,\s*)?(?:BG\s*)?\d{1,2}\.\d{1,3}(?:\s*[-–,]\s*(?:\d{1,2}\.)?\d{1,3})*\)", re.IGNORECASE
)
_BG_REF = re.compile(r"\bBG\s*\d{1,2}\.\d{1,3}\b", re.IGNORECASE)
_NEGATION = re.compile(
    r"\b(?:says?\s+nothing\s+about|(?:does\s*not|doesn[’']t|do\s*not|don[’']t|never)\s+(?:mention|name|speak\s+of|refer\s+to|discuss)"
    r"|no\s+mention\s+of|not\s+mentioned)\b",
    re.IGNORECASE,
)
# A sentence ends at . ! ? or a newline, but not at the dot inside a verse number ("BG 6.14")
_SENTENCE = re.compile(r"(?:[^.!?\n]|(?<=\d)\.(?=\d))+(?:[.!?]+[”\"']?|$)", re.MULTILINE)


def _norm(text: str) -> str:
    """Lowercase ASCII skeleton: strip diacritics, then fold common transliteration variants
    (Karthik / Kārtika -> kartik..., Mārgaśīrṣa -> margasirsa)."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    for a, b in (("th", "t"), ("dh", "d"), ("aa", "a"), ("ee", "i"), ("oo", "u"), ("w", "v")):
        text = text.replace(a, b)
    return text


_NORM_STEMS = sorted({_norm(s) for stems in PREMISE_STEMS.values() for s in stems}, key=len, reverse=True)


def _words(text: str) -> list[str]:
    n = _norm(text)
    words = re.findall(r"[a-z]+", n)
    # also join neighbours so "social media", "Raksha Bandhan" match their joined stems
    return words + [a + b for a, b in zip(words, words[1:])]


def _matches(word: str, stem: str) -> bool:
    # Short stems match whole words only ("holi" must not match "holistic", "eid" not "eidetic")
    if len(stem) <= 4:
        return word in (stem, stem + "a")
    return word.startswith(stem)


def _stems_in(text: str) -> set[str]:
    found = set()
    for w in _words(text):
        for stem in _NORM_STEMS:
            if _matches(w, stem):
                found.add(stem)
                break
    return found


def _shown_text(verses: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for v in verses:
        tr = v.get("translations")
        if isinstance(tr, dict):
            parts += [str(t.get("text", "")) for t in tr.get("english", []) if isinstance(t, dict)]
        elif isinstance(tr, list):
            parts += [str(t.get("text", "")) if isinstance(t, dict) else str(t) for t in tr]
        if v.get("translation"):
            parts.append(str(v["translation"]))
        parts += [str(c.get("text", "")) for c in v.get("context_commentary") or [] if isinstance(c, dict)]
    return " ".join(parts)


def premise_terms(query: str, verses: list[dict[str, Any]]) -> set[str]:
    """Premise stems in the question that no shown verse contains."""
    in_query = _stems_in(query)
    if not in_query:
        return set()
    shown = _stems_in(_shown_text(verses))
    return in_query - shown


def detach_premise_from_citations(answer: str, query: str, verses: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Returns (answer, warnings). See the module docstring."""
    terms = premise_terms(query, verses)
    if not terms:
        return answer, []
    warnings: list[str] = []
    out: list[str] = []
    pos = 0
    for m in _SENTENCE.finditer(answer):
        sentence = m.group(0)
        if not (_CITATION.search(sentence) or _BG_REF.search(sentence)):
            continue
        if not (_stems_in(sentence) & terms):
            continue
        out.append(answer[pos : m.start()])
        if _NEGATION.search(sentence):
            out.append(_BG_REF.sub("the text", _CITATION.sub("", sentence)))
        else:
            warnings.append(REMOVED_WARNING)
        pos = m.end()
    out.append(answer[pos:])
    cleaned = re.sub(r"[ \t]{2,}", " ", "".join(out))
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, warnings
