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
    gold_by_q = {}
    pool_by_q = defaultdict(set)
    key_by_q = defaultdict(lambda: defaultdict(list))
    routed_qs = set()

    # Discover routed queries and collect retrieved verses per question
    for system_name, data in runs:
        for row in data:
            q = row["q"]
            if row.get("routed"):
                routed_qs.add(q)
                continue
            if q not in q_order:
                q_order.append(q)
                q_types[q] = row.get("type", "")
                gold_by_q[q] = row.get("gold", [])
            for vid in row.get("retrieved", [])[:5]:
                if vid:
                    pool_by_q[q].add(vid)
                    if system_name not in key_by_q[q][vid]:
                        key_by_q[q][vid].append(system_name)

    # Filter out any questions that are routed
    active_questions = [q for q in q_order if q not in routed_qs]

    rng = random.Random(seed)
    blind_records = []
    key_records = {}

    for idx, q in enumerate(active_questions, 1):
        retrieved_set = pool_by_q[q]
        gold_list = gold_by_q.get(q, [])
        gold_set = set(gold_list)

        new_gold = [v for v in gold_list if v not in retrieved_set]

        # Union of retrieved top-5 verses and current gold list
        full_pool = retrieved_set | gold_set
        candidates = sorted(full_pool)
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
            "new_gold_count": len(new_gold),
            "pool": pool_items,
        })

        key_records[q] = {
            "q_num": idx,
            "type": q_types.get(q, ""),
            "old_gold": gold_list,
            "systems_by_verse": {vid: key_by_q[q].get(vid, []) for vid in candidates},
            "is_old_gold": {vid: (vid in gold_set) for vid in candidates},
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

    # Save blind sheet JSONL
    with open(args.sheet_jsonl, "w", encoding="utf-8") as f:
        for r in blind_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Save blind sheet readable TXT with required legend
    with open(args.sheet_txt, "w", encoding="utf-8") as f:
        f.write("# Evaluation Judging Sheet\n")
        f.write("# Legend:\n")
        f.write("#   [x] answers\n")
        f.write("#   [~] on topic but does not answer\n")
        f.write("#   blank = not relevant\n\n")
        for r in blind_records:
            f.write(f"[{r['q_num']:02d}] ({r['type']}) {r['q']}\n")
            f.write(f"Pool size: {r['pool_size']}\n")
            for item in r["pool"]:
                f.write(f"  [ ] {item['verse_id']:>6}: {item['text']}\n")
            f.write("\n")

    # Save key file
    with open(args.key_file, "w", encoding="utf-8") as f:
        json.dump(key_records, f, ensure_ascii=False, indent=2)

    total_pool = sum(r["pool_size"] for r in blind_records)
    total_new_gold = sum(r["new_gold_count"] for r in blind_records)
    print("=== POOL SUMMARY ===")
    for r in blind_records:
        print(f"Q{r['q_num']:02d} [{r['type']:<12}]: pool size = {r['pool_size']:2d}, newly added old-gold = {r['new_gold_count']:2d} | {r['q']}")
    print(f"\nTOTALS across {len(blind_records)} questions:")
    print(f"  Total unique verses in pool: {total_pool}")
    print(f"  Total newly added old-gold verses: {total_new_gold}")
    print(f"\nSaved blind sheets to:\n  - {args.sheet_jsonl}\n  - {args.sheet_txt}")
    print(f"Saved key file to:\n  - {args.key_file}")


if __name__ == "__main__":
    main()
