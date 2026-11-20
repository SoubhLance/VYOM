import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
with open("backend/data/gita/4/verses.json", encoding="utf-8") as f:
    verses = json.load(f)
v29 = next(v for v in verses if v["verse_number"] == 29)
print("v29 raw:")
print(repr(v29["text"]))
print(v29["text"])

