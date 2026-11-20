import os
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

ROOT = Path("backend").resolve()
sys.path.insert(0, str(ROOT / "indexing"))
sys.path.insert(0, str(ROOT / "retrieval"))
sys.stdout.reconfigure(encoding="utf-8")

from search import Searcher

queries = [
    ("Query 1", "how to keep composure and be virtuous"),
    ("Query 2", "how to follow celibacy"),
    ("Query 3", "if I kill a mosquito am I a sinner, will I go to hell"),
    ("Query 4", "ahimsa non-violence toward living beings"),
    ("Query 5", "what leads a person to hell"),
    ("Full 3-part query (comma-separated)", "how to keep composure and be virtuous, how to follow celibacy, if I kill a mosquito am I a sinner, will I go to hell"),
    ("Full 3-part query (question marks)", "how to keep composure and be virtuous? how to follow celibacy? if I kill a mosquito am I a sinner, will I go to hell?"),
]

s = Searcher("bge-m3")

for label, q in queries:
    results = s.search(q, k=5)
    verse_ids = [r["verse_id"] for r in results]
    scores = [round(r["score"], 4) for r in results]
    print(f"=== {label} ===")
    print(f"Query: \"{q}\"")
    print(f"Top 5 verse_ids: {verse_ids}")
    print(f"Scores: {scores}")
    print()

s.close()

