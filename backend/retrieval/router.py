"""Regex router for verse reference queries (e.g., '9.22', 'chapter 4 verse 7')."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"

_P1 = re.compile(r"(?:chapter|ch\.?)\s*(\d+)\s*[,]?\s*(?:verse|v\.?|sloka|shloka)?\s*(\d+)", re.IGNORECASE)
_P2 = re.compile(r"(?:verse|v\.?|sloka|shloka)\s*(\d+)\s*(?:of|in)\s*(?:chapter|ch\.?)\s*(\d+)", re.IGNORECASE)
_P3 = re.compile(r"\b(\d{1,2})\.(\d{1,2})\b")


def load_valid_ids() -> set[str]:
    """Load valid verse IDs (e.g. '1.1' to '18.78') from chunks.jsonl."""
    if not CHUNKS.exists():
        return set()
    with open(CHUNKS, encoding="utf-8") as f:
        return {json.loads(line)["verse_id"] for line in f if line.strip()}


def parse_verse_ref(query: str, valid_ids: set[str] | None = None) -> str | None:
    """Parse verse reference from text query.

    Returns canonical 'chapter.verse' (e.g. '9.22', '4.7') if valid, else None.
    """
    if valid_ids is None:
        valid_ids = load_valid_ids()

    m = _P1.search(query)
    if m:
        ref = f"{int(m.group(1))}.{int(m.group(2))}"
        return ref if ref in valid_ids else None

    m = _P2.search(query)
    if m:
        ref = f"{int(m.group(2))}.{int(m.group(1))}"
        return ref if ref in valid_ids else None

    m = _P3.search(query)
    if m:
        ref = f"{int(m.group(1))}.{int(m.group(2))}"
        return ref if ref in valid_ids else None

    return None
