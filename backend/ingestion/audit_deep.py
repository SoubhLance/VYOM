import re, statistics
from collections import Counter, defaultdict
from load import load_raw_verses

raw = load_raw_verses()
verses = [v for ch in raw.values() for v in ch]

for field in ("translations", "commentaries"):
    print(f"\n=== {field} ===")
    lens = defaultdict(list)
    short = defaultdict(Counter)
    for v in verses:
        for item in v[field]:
            d = (item.get("description") or "").strip()
            key = (item["author_name"], item["language"])
            lens[key].append(len(d))
            if len(d) < 40:
                short[key][d] += 1
    print(f"{'author':<28}{'lang':<9}{'empty':>6}{'<40ch':>7}{'median':>8}{'max':>8}")
    for (a, l), ls in sorted(lens.items(), key=lambda x: -statistics.median(x[1])):
        print(f"{a:<28}{l:<9}{sum(1 for x in ls if x==0):>6}{sum(1 for x in ls if x<40):>7}"
              f"{int(statistics.median(ls)):>8}{max(ls):>8}")
    print("\ncommon short strings (placeholder check):")
    for key, c in short.items():
        top = c.most_common(2)
        if top and top[0][1] > 20:
            print(" ", key, top)

# marker / artifact checks
mark = re.compile(r"।।\s*\d+\.\d+\s*।।")
print("\ntext w/ verse marker:", sum(bool(mark.search(v["text"])) for v in verses))
print("english translations containing '?':",
      sum("?" in t["description"] for v in verses for t in v["translations"] if t["language"] == "english"))
print("duplicate verse ids:", len(verses) - len({(v["chapter_number"], v["verse_number"]) for v in verses}))