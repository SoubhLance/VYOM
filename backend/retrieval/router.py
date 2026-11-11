"""Regex router for verse reference queries (e.g. '9.22', 'chapter 4 verse 7', '2.19-2.20')."""
import json
import logging
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"

logger = logging.getLogger("vyom.retrieval.router")

# Token budget guards: a range adds at most this many verses, a request forces at most this many
MAX_RANGE_VERSES = 5
MAX_FORCED_VERSES = 6

# 'chapter 4 verse 7', 'ch. 6, v. 5' (a verse word is required, so 'chapter 12' is not a verse)
_P1 = re.compile(
    r"\b(?:chapter|ch\.?)\s*(\d{1,2})\s*,?\s*(?:verse|v\.?|sloka|shloka)\s*(\d{1,3})\b", re.IGNORECASE
)
# 'verse 7 of chapter 4'
_P2 = re.compile(
    r"\b(?:verse|v\.?|sloka|shloka)\s*(\d{1,3})\s*(?:of|in)\s*(?:chapter|ch\.?)\s*(\d{1,2})\b", re.IGNORECASE
)
# '2.19-2.20', '2.19–20', '2.19 to 2.20'
_RANGE = re.compile(
    r"\b(\d{1,2})\.(\d{1,3})\s*(?:-|–|—|to\b)\s*(?:(\d{1,2})\.)?(\d{1,3})\b", re.IGNORECASE
)
# '9.22'
_P3 = re.compile(r"\b(\d{1,2})\.(\d{1,3})\b")


def load_valid_ids() -> set[str]:
    """Load valid verse IDs (e.g. '1.1' to '18.78') from chunks.jsonl."""
    if not CHUNKS.exists():
        return set()
    with open(CHUNKS, encoding="utf-8") as f:
        return {json.loads(line)["verse_id"] for line in f if line.strip()}


def _ref(ch: str | int, v: str | int) -> str:
    return f"{int(ch)}.{int(v)}"


def _expand_range(m: re.Match) -> list[str]:
    """Expand a matched range, inclusive, to at most MAX_RANGE_VERSES verses.
    A cross-chapter or non-ascending range yields only its two endpoints."""
    sc, sv = int(m.group(1)), int(m.group(2))
    ec = int(m.group(3)) if m.group(3) else sc
    ev = int(m.group(4))
    if ec != sc or ev <= sv:
        return [_ref(sc, sv), _ref(ec, ev)]
    last = min(ev, sv + MAX_RANGE_VERSES - 1)
    if last < ev:
        logger.warning(
            "VERSE_RANGE_TRUNCATED: %s kept %s-%s (max %d verses)", m.group(0), _ref(sc, sv), _ref(sc, last), MAX_RANGE_VERSES
        )
    return [_ref(sc, n) for n in range(sv, last + 1)]


def parse_verse_refs(query: str, valid_ids: set[str] | None = None) -> list[str]:
    """Return every valid verse reference in the query, in order of appearance, without duplicates.

    Ranges ('2.19-2.20', '2.19–20', '2.19 to 2.20') are expanded. Text that is matched by one
    pattern is not matched again by a later one.
    """
    if valid_ids is None:
        valid_ids = load_valid_ids()

    claimed: list[tuple[int, int]] = []
    found: list[tuple[int, list[str]]] = []
    patterns = (
        (_P1, lambda m: [_ref(m.group(1), m.group(2))]),
        (_P2, lambda m: [_ref(m.group(2), m.group(1))]),
        (_RANGE, _expand_range),
        (_P3, lambda m: [_ref(m.group(1), m.group(2))]),
    )
    for pat, to_refs in patterns:
        for m in pat.finditer(query):
            if any(m.start() < end and start < m.end() for start, end in claimed):
                continue
            claimed.append(m.span())
            found.append((m.start(), [r for r in to_refs(m) if r in valid_ids]))

    refs: list[str] = []
    for _, group in sorted(found, key=lambda x: x[0]):
        for r in group:
            if r not in refs:
                refs.append(r)
    return refs


def parse_verse_ref(query: str, valid_ids: set[str] | None = None) -> str | None:
    """Return the first valid verse reference ('9.22', '4.7') in the query, else None."""
    refs = parse_verse_refs(query, valid_ids)
    return refs[0] if refs else None


def ch13_companion(ref: str, valid_ids: set[str]) -> str | None:
    """This corpus uses 701-verse numbering: 13.1 is Arjuna's question, so the 700-verse
    13.N is 13.(N+1) here. For a chapter-13 reference return that next verse, if it exists."""
    ch, _, v = ref.partition(".")
    if ch != "13" or not v.isdigit():
        return None
    nxt = f"13.{int(v) + 1}"
    return nxt if nxt in valid_ids else None


def numbering_note(companion: str) -> str:
    """Prompt tag for a chapter-13 companion verse (no silent remapping)."""
    v = int(companion.partition(".")[2])
    return f"Numbering note: in the 700-verse numbering, this verse is 13.{v - 1}."


def build_forced_refs(refs: list[str], valid_ids: set[str], max_total: int = MAX_FORCED_VERSES) -> dict:
    """Verses that must be in context: the user's references first (at most max_total), then
    chapter-13 companions while room is left.

    Returns {"refs": [...], "notes": {vid: note}, "aliases": {companion: source_ref}, "dropped": [...]}.
    """
    forced = list(refs[:max_total])
    dropped = list(refs[max_total:])
    notes: dict[str, str] = {}
    aliases: dict[str, str] = {}
    for r in list(forced):
        comp = ch13_companion(r, valid_ids)
        if not comp or comp in forced:
            continue
        if len(forced) >= max_total:
            dropped.append(comp)
            continue
        forced.append(comp)
        notes[comp] = numbering_note(comp)
        aliases[comp] = r
    return {"refs": forced, "notes": notes, "aliases": aliases, "dropped": dropped}
