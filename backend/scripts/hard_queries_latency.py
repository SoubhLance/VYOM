"""Known-hard Sanskrit-term queries across the 6 retrieval configs + CPU retrieval latency (no LLM calls).
    .\\venv\\python.exe -I backend\\scripts\\hard_queries_latency.py
"Defining verses" are taken from the data: verses whose IAST transliteration contains the term once
diacritics, hyphens and spaces are folded away (so 'sthita-prajñasya' counts for 'sthitaprajna').
Writes backend/_scratch/hard_queries_latency.json for docs/BENCHMARK.md.
"""

import json
import statistics
import sys
import time
import unicodedata
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B / "retrieval"))
sys.path.insert(0, str(B / "indexing"))
sys.stdout.reconfigure(encoding="utf-8")

from hybrid import HybridSearcher  # noqa: E402
from search import Searcher  # noqa: E402

CONFIGS = [
    ("dense bge-m3", lambda: Searcher("bge-m3")),
    ("dense bge-base", lambda: Searcher("bge-base")),
    ("hybrid bge-m3", lambda: HybridSearcher("bge-m3")),
    ("hybrid bge-m3 --stopwords", lambda: HybridSearcher("bge-m3", stopwords=True)),
    (
        "hybrid bge-m3 --expand-always",
        lambda: HybridSearcher("bge-m3", expand_always=True),
    ),
    (
        "hybrid bge-m3 --expand-always --stopwords",
        lambda: HybridSearcher("bge-m3", expand_always=True, stopwords=True),
    ),
]
# (query as a user would type it, folded IAST stem that marks a defining verse)
# This dataset's IAST writes ś as 'sh' and svadharma as both 'sva-' and 'swa-', so stems are tuples.
HARD = [
    ("sthitaprajna", ("sthitapraj",)),
    ("What are the marks of a sthitaprajna?", ("sthitapraj",)),
    ("svadharma", ("svadharm", "swadharm")),
    ("What does the Gita say about sattva, rajas and tamas?", ("sattvamrajastama",)),
    ("sharanagati", ("sharanamvraja", "sharanamgaccha")),
]
# Passage-level credit: the sthitaprajna description runs 2.54-2.72.
PASSAGE = {("sthitapraj",): {f"2.{i}" for i in range(54, 73)}}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s if c.isalpha())


verses = [
    json.loads(line)
    for line in open(B / "data/processed/verses.jsonl", encoding="utf-8")
    if line.strip()
]
defining = {
    stem: sorted(
        {
            v["verse_id"]
            for v in verses
            if any(s in fold(v["transliteration"]) for s in stem)
        },
        key=lambda x: tuple(map(int, x.split("."))),
    )
    for _, stem in HARD
}
for stem, ids in defining.items():
    print(f"defining verses for {stem!r}: {ids}")

eval_qs = [
    json.loads(line)["q"]
    for line in open(B / "retrieval/eval/questions.v2.jsonl", encoding="utf-8")
    if line.strip()
]

out = {"defining": defining, "configs": {}}
for name, make in CONFIGS:
    t0 = time.perf_counter()
    eng = make()
    load_s = time.perf_counter() - t0
    try:
        eng.search("warm up", k=10, n_chunks=50)
        times = []
        for q in eval_qs:
            t = time.perf_counter()
            eng.search(q, k=10, n_chunks=50)
            times.append((time.perf_counter() - t) * 1000)
        hard = {}
        for q, stem in HARD:
            top5 = [r["verse_id"] for r in eng.search(q, k=5, n_chunks=50)]
            hits = [v for v in top5 if v in defining[stem]]
            in_passage = [v for v in top5 if v in PASSAGE.get(stem, set())]
            hard[q] = {"top5": top5, "defining_hits": hits, "passage_hits": in_passage}
    finally:
        eng.close()
    times.sort()
    lat = {
        "load_s": round(load_s, 1),
        "median_ms": round(statistics.median(times)),
        "p95_ms": round(times[int(0.95 * (len(times) - 1))]),
        "max_ms": round(times[-1]),
    }
    out["configs"][name] = {"latency": lat, "hard": hard}
    print(
        f"\n== {name}: latency median {lat['median_ms']} ms, p95 {lat['p95_ms']} ms (load {lat['load_s']} s)"
    )
    for q, r in hard.items():
        print(
            f"   {q!r}: top5={r['top5']}  defining hits={r['defining_hits'] or '-'}  passage hits={r['passage_hits'] or '-'}"
        )

(B / "_scratch/hard_queries_latency.json").write_text(
    json.dumps(
        {**out, "defining": {"|".join(k): v for k, v in out["defining"].items()}},
        ensure_ascii=False,
        indent=1,
    ),
    encoding="utf-8",
)
