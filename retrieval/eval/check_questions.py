# retrieval/eval/check_questions.py
import json, sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ingestion"))
from clean import load_clean

TYPES = {"lookup", "conceptual", "word_meaning", "multi_verse"}
verses = {v["verse_id"]: v for v in load_clean()}
path = Path(__file__).with_name("questions.jsonl")

errors, counts = 0, Counter()
for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
    if not line.strip():
        continue
    try:
        q = json.loads(line)
    except json.JSONDecodeError as e:
        print(f"line {n}: invalid JSON ({e})"); errors += 1; continue

    problems = []
    if not q.get("q"): problems.append("missing q")
    if q.get("type") not in TYPES: problems.append(f"bad type {q.get('type')!r}")
    gold = q.get("gold") or []
    if not gold: problems.append("empty gold")
    bad = [g for g in gold if g not in verses]
    if bad: problems.append(f"unknown verse ids {bad}")

    counts[q.get("type")] += 1
    print(f"\n[{n}] ({q.get('type')}) {q.get('q')}")
    for g in gold:
        if g in verses:
            t = verses[g]["translations"]["english"][0]["text"]
            print(f"     {g}: {t[:110]}")
    if problems:
        errors += 1
        print("     !!", "; ".join(problems))

print("\ncounts:", dict(counts), "| total:", sum(counts.values()), "| lines with errors:", errors)