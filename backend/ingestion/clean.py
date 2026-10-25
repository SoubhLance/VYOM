import re, unicodedata
from load import load_raw_verses

MARKER = re.compile(r"(?:।।|\|\|)\s*(?:\d+\.)?\d+\s*(?:।{1,2}|\|{1,2})")

# ── threshold for the future chunking stage ──────────────────────────
# chunk.py will use this to decide which commentaries are long enough to
# embed on their own.  clean.py itself does NOT filter on length; every
# non-empty commentary survives cleaning.
EMBED_MIN_COMMENTARY_CHARS = 40  # used by chunk.py to decide what gets embedded, NOT by clean.py


def norm(s: str | None, keep_lines: bool = False) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = MARKER.sub("", s)
    if keep_lines:
        lines = [re.sub(r"[ \t]+", " ", l).strip() for l in s.splitlines()]
        return "\n".join(l for l in lines if l)
    return re.sub(r"\s+", " ", s).strip()


_GLUED_SENT = re.compile(r"(?<=[a-z])\.(?=[A-Z])")
_GLUED_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")
_EDITORIAL_LABEL = re.compile(r"^(?:Fix|Fixed|Corrected|Correction|Revised):\s*")
_FIX_LABEL = _EDITORIAL_LABEL


def strip_fix_label(text: str) -> str:
    """Strip only a leading editorial label ('Fix:', 'Fixed:', 'Corrected:',
    'Correction:', 'Revised:') and following whitespace if present."""
    return _EDITORIAL_LABEL.sub("", text) if text else ""


_LEADING_PERIOD = re.compile(r"^\.\s+")
_RANGE_HEADING = re.compile(r"^(?:।।|\|\|)\s*\d+\.\d+\s*(?:--|–|-)\s*\d+\.\d+\s*(?:।।|\|\|)\s*")
_FOOTNOTE_REF = re.compile(r"\s*\(\s*टिप्पणी[^\)]*?\d+(?:\.\d+)?\s*\)")
_LEADING_A = re.compile(r"^\(a\)\s*")
_INLINE_PARTS = re.compile(r"\s*\([b-d]\)\s*")


def strip_letter_markers(text: str, author: str = "", language: str = "english") -> str:
    """Strip leading '(a)' and inline '(b)', '(c)', '(d)' markers from English translations.

    Only strips if leading '(a)' is present AND (a later '(b)' exists OR author is Swami Adidevananda).
    Inline markers are replaced with a single space.
    """
    if language == "english" and _LEADING_A.match(text):
        if "(b)" in text or author == "Swami Adidevananda":
            text = _LEADING_A.sub("", text)
            text = _INLINE_PARTS.sub(" ", text).strip()
    return text


def strip_leading_period(text: str) -> str:
    """Strip a leading lone period + space at start of translation."""
    return _LEADING_PERIOD.sub("", text) if text else ""


def clean_stray_danda(text: str) -> str:
    """Remove stray Bengali ishar '৷' (U+09F7) markers and repair spacing/punctuation."""
    if not text:
        return ""
    if "৷" not in text:
        return text
    # 1. Punctuation followed by dandas/dots: preserve punctuation, drop dandas/dots
    text = re.sub(r"([!?])(?:\s*[৷.]\s*)+", r"\1 ", text)
    text = re.sub(r"\.(?:\s*[৷.]\s*)+", ". ", text)
    # 2. Word followed by dandas + dot -> word.
    text = re.sub(r"(?<=\w)\s*৷+\.\s*", ". ", text)
    # 3. Any remaining lone ৷+ -> single space
    text = re.sub(r"\s*৷+\s*", " ", text)
    # 4. Clean artifacts
    text = re.sub(r"([!?])\.\s*", r"\1 ", text)
    text = re.sub(r"\s+\.", ".", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_ramsukhdas(text: str, is_translation: bool = True) -> str:
    """Strip verse-range headings (translations only) and inline footnote references from Ramsukhdas."""
    if not text:
        return ""
    if is_translation:
        text = _RANGE_HEADING.sub("", text)
    text = _FOOTNOTE_REF.sub("", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def strip_hindi_footnote(text: str, author: str = "") -> str:
    """Strip Hindi footnote references (kept for backwards compatibility)."""
    return clean_ramsukhdas(text, is_translation=True)


def clean_sivananda(text: str) -> str:
    """Raw form: '<verse no.> <word-by-word gloss> Commentary <real text>'.
    Returns only the real text, or None if there is none."""
    if "Commentary" not in text:
        return None
    body = text.split("Commentary", 1)[1].strip()
    if not body:
        return None
    body = body.replace("?", ",")               # '?' is a lost-punctuation placeholder here
    body = _GLUED_SENT.sub(". ", body)          # 'gift.Next' -> 'gift. Next'
    body = _GLUED_CAMEL.sub(" ", body)          # 'andThen' -> 'and Then'
    return re.sub(r"\s+", " ", body).strip()


def clean_verse(v: dict) -> dict:
    translations = {"english": [], "hindi": []}
    for t in v["translations"]:
        text = norm(t["description"])
        text = strip_fix_label(text)
        text = strip_leading_period(text)
        author = t["author_name"]
        lang = t["language"]
        if lang == "english":
            text = strip_letter_markers(text, author=author, language=lang)
            text = clean_stray_danda(text)
        elif lang == "hindi":
            text = text.replace("৷", "।")
            if "Ramsukhdas" in author:
                text = clean_ramsukhdas(text, is_translation=True)
        if text:
            translations[lang].append({"author": author, "text": text})

    commentaries = []
    for c in v["commentaries"]:
        text = norm(c["description"])
        text = strip_fix_label(text)
        author = c["author_name"]
        lang = c["language"]
        if author == "Swami Sivananda" and lang == "english":
            text = clean_sivananda(text) or ""
            text = clean_stray_danda(text)
        else:
            text = text.replace("৷", "।")
            if "Ramsukhdas" in author and lang == "hindi":
                text = clean_ramsukhdas(text, is_translation=False)
        if text:
            commentaries.append({"author": author, "language": lang, "text": text})

    return {
        "verse_id": f'{v["chapter_number"]}.{v["verse_number"]}',
        "chapter": v["chapter_number"],
        "verse": v["verse_number"],
        "sanskrit": norm(v["text"], keep_lines=True).replace("৷", "।"),
        "transliteration": norm(v["transliteration"], keep_lines=True).replace("৷", "।"),
        "word_meanings": norm(v["word_meanings"]).replace("৷", "।"),
        "translations": translations,
        "commentaries": commentaries,
    }


def load_clean() -> list[dict]:
    return [clean_verse(v) for ch in load_raw_verses().values() for v in ch]


if __name__ == "__main__":
    data = load_clean()
    print(len(data), "verses cleaned")
    import json
    print(json.dumps(next(d for d in data if d["verse_id"] == "2.47"), ensure_ascii=False, indent=2))