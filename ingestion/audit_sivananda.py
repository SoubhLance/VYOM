# ingestion/audit_sivananda.py
import re, random
from load import load_raw_verses

raw = load_raw_verses()
verses = [v for ch in raw.values() for v in ch]
BUG = re.compile(r"\?\s+[a-z]")     # '?' followed by lowercase = probably a lost , or ;
DEVA = re.compile(r"[\u0900-\u097F]")

print("--- A. '?'+lowercase in ENGLISH TRANSLATIONS ---")
n = 0
for v in verses:
    for t in v["translations"]:
        if t["language"] == "english":
            for m in BUG.finditer(t["description"]):
                n += 1
                if n <= 10:
                    s = t["description"]
                    print(f'{v["chapter_number"]}.{v["verse_number"]} {t["author_name"]}: '
                          f'{s[max(0, m.start()-40):m.end()+30]!r}')
print("total:", n)

sv = []
for v in verses:
    for c in v["commentaries"]:
        if (c["author_name"] == "Swami Sivananda" and c["language"] == "english"
                and c["description"].strip()):
            sv.append((f'{v["chapter_number"]}.{v["verse_number"]}', c["description"].strip()))

print(f"\n--- B. Sivananda commentary: {len(sv)} entries ---")
print("start with Devanagari:", sum(bool(DEVA.match(t)) for _, t in sv))
print("contain 'Commentary':", sum("Commentary" in t for _, t in sv))
print("contain '?'+lowercase:", sum(bool(BUG.search(t)) for _, t in sv))
print("'.' glued to capital:", sum(bool(re.search(r"[a-z]\.[A-Z]", t)) for _, t in sv))

print("\nentries WITHOUT 'Commentary' (first 8):")
for vid, t in [x for x in sv if "Commentary" not in x[1]][:8]:
    print(" ", vid, repr(t[:140]))

print("\nrandom samples, 200 chars from 'Commentary' onward:")
random.seed(1)
pool = [x for x in sv if "Commentary" in x[1]]
for vid, t in random.sample(pool, min(4, len(pool))):
    i = t.index("Commentary")
    print(" ", vid, repr(t[i:i + 200]))