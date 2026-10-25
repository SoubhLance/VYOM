import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "gita"


def load_chapters() -> list[dict]:
    with open(DATA_DIR / "chapters.json", encoding="utf-8") as f:
        return json.load(f)


def load_raw_verses() -> dict[int, list[dict]]:
    """Returns {chapter_number: [raw verse dicts]} with no transformation."""
    out = {}
    for ch in range(1, 19):
        path = DATA_DIR / str(ch) / "verses.json"
        with open(path, encoding="utf-8") as f:
            out[ch] = json.load(f)
    return out