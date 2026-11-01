import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend" / "data" / "processed" / "verses.jsonl"
OUTPUT = ROOT / "frontend" / "public" / "translations"


def main():
    records = []
    with open(SOURCE, "r", encoding="utf-8", newline="") as source_file:
        for line in source_file:
            if line.strip():
                records.append(json.loads(line))

    first_seen = []
    coverage = defaultdict(set)
    english_by_verse = {}
    for record in records:
        verse_id = record["verse_id"]
        entries = record.get("translations", {}).get("english", [])
        english_by_verse[verse_id] = entries
        for entry in entries:
            author = entry["author"]
            if author not in first_seen:
                first_seen.append(author)
            if entry.get("text", "").strip():
                coverage[author].add(verse_id)

    first_author = next(
        entry["author"]
        for entry in english_by_verse.get("18.66", [])
        if entry.get("text", "").strip()
    )
    authors = [first_author] + sorted(
        (author for author in first_seen if author != first_author),
        key=lambda author: (-len(coverage[author]), first_seen.index(author)),
    )
    author_rank = {author: index for index, author in enumerate(authors)}

    chapters = {chapter: {} for chapter in range(1, 19)}
    for record in records:
        entries = sorted(
            english_by_verse.get(record["verse_id"], []),
            key=lambda entry: author_rank[entry["author"]],
        )
        chapters[record["chapter"]][record["verse_id"]] = [
            {"author": entry["author"], "text": entry.get("text", "")}
            for entry in entries
        ]

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for chapter, verses in chapters.items():
        path = OUTPUT / f"ch{chapter:02d}.json"
        payload = json.dumps(verses, ensure_ascii=False, indent=2) + "\n"
        with open(path, "w", encoding="utf-8", newline="") as output_file:
            output_file.write(payload)
        print(f"{path}: {len(payload.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
