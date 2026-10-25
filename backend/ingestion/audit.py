from collections import Counter
from load import load_chapters, load_raw_verses

# Commonly cited per-chapter verse counts (sum = 701). Deviations are
# flagged, not assumed wrong: some editions merge verses (e.g. 1.16-18).
EXPECTED = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]


def is_empty(v):
    return v is None or (isinstance(v, (str, list, dict)) and len(v) == 0)


def main():
    chapters = load_chapters()
    print(f"chapters.json: {len(chapters)} entries")
    print("chapter keys:", sorted(chapters[0].keys()), "\n")

    raw = load_raw_verses()
    all_verses = [v for ch in raw.values() for v in ch]
    print(f"total verses: {len(all_verses)}")

    # 1. Count per chapter vs expected
    for ch, verses in raw.items():
        exp = EXPECTED[ch - 1]
        flag = "" if len(verses) == exp else f"  <-- expected {exp}"
        print(f"  ch {ch:>2}: {len(verses)}{flag}")

    # 2. Field presence / emptiness
    print("\nfield coverage (present / non-empty):")
    keys = Counter(k for v in all_verses for k in v)
    for k, n in keys.most_common():
        non_empty = sum(1 for v in all_verses if not is_empty(v.get(k)))
        print(f"  {k:<20} {n:>4} present, {non_empty:>4} non-empty")

    # 3. Nested structures (translations / commentaries etc.)
    for k in keys:
        sample = next((v[k] for v in all_verses if isinstance(v.get(k), list) and v[k]), None)
        if sample and isinstance(sample[0], dict):
            print(f"\n'{k}' item keys:", sorted(sample[0].keys()))
            authors = Counter(
                (i.get("author_name") or i.get("author"), i.get("language"))
                for v in all_verses for i in (v.get(k) or [])
            )
            for a, n in authors.most_common(15):
                print(f"    {a}: {n}")

    # 4. One full sample verse
    import json
    print("\nsample verse (2.47 if found):")
    pick = next((v for v in raw[2] if "47" in str(v.get("verse_number", v.get("verse", "")))), raw[2][0])
    print(json.dumps(pick, ensure_ascii=False, indent=2)[:2500])


    print("\n--- 5. '?' glued between letters in english translations ---")
    pat = re.compile(r"\w\?\w")
    n = 0
    for v in verses:
        for t in v["translations"]:
            if t["language"] == "english":
                for m in pat.finditer(t["description"]):
                    n += 1
                    if n <= 15:
                        s = t["description"]
                        print(f'{v["chapter_number"]}.{v["verse_number"]} {t["author_name"]}: '
                            f'{s[max(0, m.start()-40):m.end()+40]!r}')
    print("total:", n)

if __name__ == "__main__":
    main()