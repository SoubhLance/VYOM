"""Pooling review: union top-5 retrieved verses across N runs for blind judging.
Run from repo root:
    python retrieval/eval/pool_review.py
    python retrieval/eval/pool_review.py retrieval/eval/results/bge-m3_dense.json ...
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ingestion"))
sys.stdout.reconfigure(encoding="utf-8")

from clean import load_clean  # noqa: E402

QUESTIONS = ROOT / "retrieval" / "eval" / "questions.jsonl"
RES = ROOT / "retrieval" / "eval" / "results"

DEFAULT_FILES = [
    RES / "bge-m3_dense.json",
    RES / "bge-base_dense.json",
    RES / "bge-m3_hybrid.json",
    RES / "bge-m3_hybrid_sw.json",
    RES / "bge-m3_hybrid_ea.json",
    RES / "bge-m3_hybrid_ea_sw.json",
]


def load_verses():
    return {v["verse_id"]: v for v in load_clean()}


def get_verse_text(verses, vid: str) -> str:
    if vid in verses and verses[vid].get("translations", {}).get("english"):
        return verses[vid]["translations"]["english"][0]["text"]
    return ""


def build_pool(file_paths, seed: int = 42):
    verses = load_verses()
    runs = []
    for p in file_paths:
        p = Path(p)
        system_name = p.stem
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        runs.append((system_name, data))

    q_order = []
    q_types = {}
    pool_by_q = defaultdict(set)
    key_by_q = defaultdict(lambda: defaultdict(list))

    for system_name, data in runs:
        for row in data:
            q = row["q"]
            if q not in q_order:
                q_order.append(q)
                q_types[q] = row.get("type", "")
            for vid in row.get("retrieved", [])[:5]:
                if vid:
                    pool_by_q[q].add(vid)
                    if system_name not in key_by_q[q][vid]:
                        key_by_q[q][vid].append(system_name)

    rng = random.Random(seed)
    blind_records = []
    key_records = {}

    for idx, q in enumerate(q_order, 1):
        candidates = sorted(pool_by_q[q])
        rng.shuffle(candidates)

        pool_items = []
        for vid in candidates:
            pool_items.append({
                "verse_id": vid,
                "text": get_verse_text(verses, vid),
            })

        blind_records.append({
            "q_num": idx,
            "q": q,
            "type": q_types.get(q, ""),
            "pool_size": len(candidates),
            "pool": pool_items,
        })

        key_records[q] = {
            "q_num": idx,
            "type": q_types.get(q, ""),
            "systems_by_verse": dict(key_by_q[q]),
        }

    return blind_records, key_records


def main():
    ap = argparse.ArgumentParser(description="Pool retrieval results for blind judging.")
    ap.add_argument("files", nargs="*", default=[], help="Result JSON files to pool.")
    ap.add_argument("--files", nargs="+", dest="opt_files", help="List of result JSON files to pool.")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for shuffling.")
    ap.add_argument("--sheet-jsonl", type=Path, default=ROOT / "retrieval" / "eval" / "blind_sheet.jsonl", help="Blind sheet JSONL path.")
    ap.add_argument("--sheet-txt", type=Path, default=ROOT / "retrieval" / "eval" / "blind_sheet.txt", help="Blind sheet TXT path.")
    ap.add_argument("--key-file", type=Path, default=ROOT / "retrieval" / "eval" / "pool_key.json", help="Key file path.")
    args = ap.parse_args()

    files = [Path(p) for p in args.opt_files] if args.opt_files else ([Path(p) for p in args.files] if args.files else DEFAULT_FILES)

    blind_records, key_records = build_pool(files, seed=args.seed)

    with open(args.sheet_jsonl, "w", encoding="utf-8") as f:
        for r in blind_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(args.sheet_txt, "w", encoding="utf-8") as f:
        for r in blind_records:
            f.write(f"[{r['q_num']:02d}] ({r['type']}) {r['q']}\n")
            f.write(f"Pool size: {r['pool_size']}\n")
            for item in r["pool"]:
                f.write(f"  [ ] {item['verse_id']:>6}: {item['text']}\n")
            f.write("\n")

    with open(args.key_file, "w", encoding="utf-8") as f:
        json.dump(key_records, f, ensure_ascii=False, indent=2)

    total_pool = sum(r["pool_size"] for r in blind_records)
    print("=== POOL SUMMARY ===")
    for r in blind_records:
        print(f"Q{r['q_num']:02d} [{r['type']:<12}]: {r['pool_size']:2d} verses | {r['q']}")
    print(f"\nTOTAL UNIQUE VERSES ACROSS ALL QUESTIONS: {total_pool}")
    print(f"\nSaved blind sheets to:\n  - {args.sheet_jsonl}\n  - {args.sheet_txt}")
    print(f"Saved key file to:\n  - {args.key_file}")


if __name__ == "__main__":
    main()
