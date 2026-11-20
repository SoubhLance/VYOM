import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

targets = [
    (17, 14),
    (13, 7),
    (16, 2),
    (16, 21),
    (18, 17),
    (10, 5),
]

for ch, v in targets:
    p = Path(f"backend/data/gita/{ch}/verses.json")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    matching = [x for x in data if x.get("verse_number") == v]
    if not matching:
        print(f"Verse {ch}.{v} NOT FOUND in {p}")
        continue
    item = matching[0]
    raw_text = item.get("text", "")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    first_deva = lines[0] if lines else ""
    translit = item.get("transliteration", "")
    print(f"=== Bhagavad Gita {ch}.{v} ===")
    print(f"First Devanagari line:\n{first_deva}")
    print(f"Transliteration:\n{translit}")
    print()

