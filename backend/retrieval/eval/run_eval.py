"""Retrieval eval. Run from repo root:
    python retrieval/eval/run_eval.py --mode dense
    python retrieval/eval/run_eval.py --mode hybrid
Queries that name a verse ('9.22', 'chapter 4 verse 7') go to the regex router unless --no-router.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "retrieval"))
sys.stdout.reconfigure(encoding="utf-8")

from hybrid import HybridSearcher  # noqa: E402
from router import load_valid_ids, parse_verse_ref  # noqa: E402
from search import Searcher  # noqa: E402

QUESTIONS = ROOT / "retrieval" / "eval" / "questions.jsonl"
RESULTS = ROOT / "retrieval" / "eval" / "results"
K = 5


def load_questions(path=QUESTIONS):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def score(retrieved, gold, k=K, q=""):
    if not gold:
        raise ValueError(f"Empty gold for question: '{q}'")
    top = retrieved[:k]
    found = [g for g in gold if g in top]
    hit = 1.0 if found else 0.0
    recall = len(found) / min(len(gold), k)  # capped: a 7-gold question can't exceed 5/7 at k=5
    rr = next((1 / i for i, v in enumerate(retrieved, 1) if v in gold), 0.0)
    return hit, recall, rr


def run_model(key, questions, mode, use_router, expand_always=False, stopwords=False, n_chunks=50):
    if mode == "hybrid":
        engine = HybridSearcher(key, expand_always=expand_always, stopwords=stopwords)
    else:
        engine = Searcher(key)  # one Qdrant client at a time
    valid_ids = load_valid_ids()
    rows = []
    try:
        for q in questions:
            ref = parse_verse_ref(q["q"], valid_ids) if use_router else None
            retrieved = [ref] if ref else [r["verse_id"] for r in engine.search(q["q"], k=10, n_chunks=n_chunks)]
            hit, rec, rr = score(retrieved, q["gold"], q=q.get("q", ""))
            rows.append({**q, "routed": bool(ref), "retrieved": retrieved, "hit": hit, "recall": rec, "rr": rr})
    finally:
        engine.close()
    return rows


def summarize(title, rows):
    groups = defaultdict(list)
    for r in rows:
        groups[("routed:" if r["routed"] else "") + r["type"]].append(r)
        groups["ALL"].append(r)
    print(f"\n=== {title} (k={K}) ===")
    print(f"{'type':<20}{'n':>3}  {'hit@5':>6}  {'recall@5':>8}  {'MRR@10':>6}")
    for t in [*sorted(g for g in groups if g != "ALL"), "ALL"]:
        g = groups[t]
        n = len(g)
        print(f"{t:<20}{n:>3}  {sum(x['hit'] for x in g)/n:>6.2f}  "
              f"{sum(x['recall'] for x in g)/n:>8.2f}  {sum(x['rr'] for x in g)/n:>6.2f}")
    print("\nmisses (no gold in top 5):")
    for r in rows:
        if not r["hit"]:
            print(f"  [{r['type']}] {r['q']}\n     gold={r['gold']}  got={r['retrieved'][:5]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["dense", "hybrid"], default="dense")
    ap.add_argument("--model", "--models", dest="models", nargs="+", default=["bge-m3", "bge-base"], choices=["bge-m3", "bge-base"])
    ap.add_argument("--no-router", action="store_true")
    ap.add_argument("--expand-always", action="store_true")
    ap.add_argument("--stopwords", action="store_true")
    ap.add_argument("--n-chunks", type=int, default=50)
    ap.add_argument("--questions", type=Path, default=QUESTIONS)
    args = ap.parse_args()

    if args.mode == "dense" and (args.expand_always or args.stopwords):
        print("Note: --expand-always and --stopwords are only relevant in hybrid mode and are ignored in dense mode.")

    questions_path = Path(args.questions)
    questions = load_questions(questions_path)
    RESULTS.mkdir(exist_ok=True)
    for key in args.models:
        rows = run_model(
            key,
            questions,
            args.mode,
            not args.no_router,
            expand_always=args.expand_always,
            stopwords=args.stopwords,
            n_chunks=args.n_chunks,
        )
        parts = [key, args.mode]
        extras = []
        if args.mode == "hybrid":
            if args.expand_always:
                parts.append("ea")
                extras.append("ea")
            if args.stopwords:
                parts.append("sw")
                extras.append("sw")
        if args.no_router:
            parts.append("norouter")
            extras.append("norouter")
        if args.n_chunks != 50:
            parts.append(f"n{args.n_chunks}")
            extras.append(f"n{args.n_chunks}")
        if questions_path.resolve() != QUESTIONS.resolve():
            parts.append(questions_path.stem)
            extras.append(questions_path.stem)
        filename = "_".join(parts) + ".json"
        with open(RESULTS / filename, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        tag = f"{key} / {args.mode}"
        if extras:
            tag += f" ({', '.join(extras)})"
        summarize(f"{tag} [provisional (pre-pooling)]", rows)


if __name__ == "__main__":
    main()
