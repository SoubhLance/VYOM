"""Export the verse text the chat needs (Sanskrit, transliteration, word meanings) per chapter.

Source of truth: backend/data/processed/verses.jsonl (read only). Output:
frontend/public/verses/chNN.json = {"2.47": {"sanskrit", "transliteration", "word_meanings",
"translation": {"author", "text"}}, ...}. "translation" is english[0], the one the LLM prompt shows.
All English translations (for the reader's picker) stay in public/translations/chNN.json.
Generated file: don't hand-edit, rerun this script.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend" / "data" / "processed" / "verses.jsonl"
OUTPUT = ROOT / "frontend" / "public" / "verses"
FIELDS = ("sanskrit", "transliteration", "word_meanings")


def main():
    chapters = {chapter: {} for chapter in range(1, 19)}
    with open(SOURCE, "r", encoding="utf-8", newline="") as source_file:
        for line in source_file:
            if not line.strip():
                continue
            record = json.loads(line)
            entry = {field: record.get(field, "") or "" for field in FIELDS}
            # The translation the LLM prompt shows (prompt_v2 sends english[0]) and the quote
            # verifier matches against: chat cards and the verse modal show the same one.
            english = (record.get("translations") or {}).get("english") or []
            if english:
                entry["translation"] = {
                    "author": english[0].get("author", ""),
                    "text": english[0].get("text", ""),
                }
            chapters[record["chapter"]][record["verse_id"]] = entry

    total = sum(len(verses) for verses in chapters.values())
    if total != 701:
        raise SystemExit(f"expected 701 verses, found {total}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for chapter, verses in chapters.items():
        path = OUTPUT / f"ch{chapter:02d}.json"
        payload = json.dumps(verses, ensure_ascii=False, separators=(",", ":")) + "\n"
        with open(path, "w", encoding="utf-8", newline="") as output_file:
            output_file.write(payload)
        print(f"{path}: {len(verses)} verses, {len(payload.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
