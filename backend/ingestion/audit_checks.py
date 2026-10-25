import re
from collections import Counter
from load import load_raw_verses

raw = load_raw_verses()
verses = [v for ch in raw.values() for v in ch]
MARK = re.compile(r"।।\s*\d+\.\d+\s*।।")

print("--- 1. verse(s) without marker ---")
for v in verses:
    if not MARK.search(v["text"]):
        print(f'{v["chapter_number"]}.{v["verse_number"]}', repr(v["text"][-70:]))

print("\n--- 2. ALL commentary authors (no cap) ---")
c = Counter((i["author_name"], i["language"]) for v in verses for i in v["commentaries"])
print(len(c), "authors")
for k, n in c.most_common():
    print(f"{n:>5}  {k}")

print("\n--- 3. verses with empty commentary ---")
for v in verses:
    e = [i["author_name"] for i in v["commentaries"] if not (i.get("description") or "").strip()]
    if e:
        print(f'{v["chapter_number"]}.{v["verse_number"]}', e)

print("\n--- 4. '?' in english translations (8 samples) ---")
shown = 0
for v in verses:
    for t in v["translations"]:
        d = t["description"]
        if t["language"] == "english" and "?" in d and shown < 8:
            i = d.index("?")
            print(f'{v["chapter_number"]}.{v["verse_number"]} {t["author_name"]}: ...{d[max(0, i-50):i+30]!r}')
            shown += 1
