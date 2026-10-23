# ingestion/audit_sivananda2.py
import re, random, statistics
from load import load_raw_verses

raw = load_raw_verses()
verses = [v for ch in raw.values() for v in ch]


def sivananda(v):
    for c in v["commentaries"]:
        if c["author_name"] == "Swami Sivananda" and c["language"] == "english":
            return (c["description"] or "").strip()
    return ""


def body(text):
    """Proposed: drop the word-by-word gloss, keep text after the first 'Commentary'."""
    if "Commentary" not in text:
        return None
    return text.split("Commentary", 1)[1].strip()


def fix(text):
    text = re.sub(r"\?(?=\s+[a-z])", ",", text)          # lost comma/semicolon before lowercase
    text = re.sub(r"([a-z])\.([A-Z])", r"\1. \2", text)  # glued sentences
    return text


bodies, no_comm = {}, []
for v in verses:
    vid = f'{v["chapter_number"]}.{v["verse_number"]}'
    t = sivananda(v)
    if not t:
        continue
    b = body(t)
    if b is None:
        no_comm.append((vid, t))
    else:
        bodies[vid] = b

print(f"--- 1. entries without 'Commentary': {len(no_comm)} ---")
for vid, t in no_comm:
    print(f"  {vid}: len={len(t)} tail={t[-120:]!r}")

print("\n--- 2. letters lost? ('qu' and apostrophes) ---")
trans = " ".join(t["description"] for v in verses for t in v["translations"] if t["language"] == "english")
comm = " ".join(bodies.values())
for name, s in (("english translations", trans), ("sivananda body", comm)):
    print(f"{name}: chars={len(s)}  'qu'={s.lower().count('qu')}  "
          f"apostrophes={s.count(chr(39)) + s.count(chr(8217))}")
print("'coner':", len(re.findall(r"\bconer\b", comm.lower())),
      "| 'conquer':", len(re.findall(r"\bconquer", comm.lower())))

print("\n--- 3. after proposed fix ---")
fixed = {k: fix(b) for k, b in bodies.items()}
print("'?' in bodies: before =", sum(b.count("?") for b in bodies.values()),
      "after =", sum(b.count("?") for b in fixed.values()))
cap = re.compile(r"\?\s+[A-Z]")
print("remaining '?' followed by a capital:", sum(len(cap.findall(b)) for b in fixed.values()))
n = shown = 0
for vid, b in fixed.items():
    for m in cap.finditer(b):
        n += 1
        if n % 25 == 1 and shown < 10:
            shown += 1
            print(f"  {vid}: {b[max(0, m.start()-60):m.end()+30]!r}")

lens = [len(b) for b in fixed.values()]
print(f"\n--- 4. body length (chars): median={int(statistics.median(lens))} max={max(lens)} "
      f"over 1200: {sum(l > 1200 for l in lens)} of {len(lens)} ---")

random.seed(3)
print("\n--- 5. before/after, 3 random verses ---")
for vid in random.sample(list(fixed), 3):
    print(f"{vid} BEFORE: {bodies[vid][:260]!r}")
    print(f"{vid} AFTER : {fixed[vid][:260]!r}\n")