import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
with open("backend/data/gita/4/verses.json", encoding="utf-8") as f:
    verses = json.load(f)
v29 = next(v for v in verses if v["verse_number"] == 29)
raw_line1 = v29["text"].split('।')[0].strip()
print("Raw line 1:", repr(raw_line1))
for c in raw_line1:
    print(f"{c}: U+{ord(c):04X}")

