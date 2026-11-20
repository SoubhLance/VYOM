"""Hindi / Hinglish queries on dense bge-m3 vs dense bge-base (local, no LLM).
    .\\venv\\python.exe -I backend\\scripts\\hindi_check.py
Expected verses are the standard ones for each topic, listed for reading the output, not as gold.
"""

import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B / "retrieval"))
sys.path.insert(0, str(B / "indexing"))
sys.stdout.reconfigure(encoding="utf-8")

from search import Searcher  # noqa: E402

QUERIES = [
    ("मन को कैसे नियंत्रित करें?", "mind control: 6.26, 6.34, 6.35"),
    ("karma yoga kya hai", "karma yoga: 2.47, 2.48, 3.3-3.9"),
    ("आत्मा अमर है", "immortal self: 2.12, 2.17-2.25"),
    ("man ko shant kaise karein", "calming the mind: 6.26, 6.35, 2.70"),
    ("How do I control my mind?", "English control: 6.26, 6.34, 6.35"),
]
for model in ("bge-m3", "bge-base"):
    s = Searcher(model)
    try:
        print(f"\n== dense {model}")
        for q, note in QUERIES:
            hits = s.search(q, k=5)
            print(
                f"  {q!r:<34} -> {', '.join(f'{h['verse_id']} ({h['score']:.2f})' for h in hits)}   [{note}]"
            )
    finally:
        s.close()
