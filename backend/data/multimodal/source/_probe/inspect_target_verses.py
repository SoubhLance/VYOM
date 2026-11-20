import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

for ch, vn in [(1, 26), (1, 27), (1, 28), (1, 36), (1, 37), (1, 46), (4, 29), (4, 30), (4, 31)]:
    with open(f"backend/data/gita/{ch}/verses.json", encoding="utf-8") as f:
        verses = json.load(f)
    v = next(x for x in verses if x["verse_number"] == vn)
    print(f"=== Ch {ch} Verse {vn} ===")
    print("Raw:", repr(v["text"]))

