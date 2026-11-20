"""Warm the running server's answer cache before a demo.

Start the servers first (npm run dev:win), then from the repo root:
    .\\venv\\python.exe backend\\scripts\\warm_cache.py              # demo chips + typed demo questions
    .\\venv\\python.exe backend\\scripts\\warm_cache.py --list       # only print chip label -> query mapping
    .\\venv\\python.exe backend\\scripts\\warm_cache.py --all-chips  # every chip in SuggestedChips.tsx

The cache key is the exact query text (normalized for case/whitespace/trailing punctuation), and chips send
their `query`, not their label, so chip queries are read straight from the frontend source.
Requests go out like the frontend's ({"multi": true, "top_k": 5}), --gap seconds apart (Groq: 8K tokens/min),
printing X-VYOM-Cache and X-LLM-Provider. The cache lives in the backend process: a restart empties it.
"""

import argparse
import re
import sys
import time
from pathlib import Path

import httpx

CHIPS_TSX = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "components"
    / "SuggestedChips.tsx"
)

# Chip labels to warm by default (as shown on screen), plus typed questions that have no chip.
DEMO_CHIP_LABELS = [
    "The Cosmic Vision of Time",
    "How to master an agitated mind?",
    "Explain BG 2.47 Nishkama Karma",
    "Nishkama Karma in Modern Life",
]
DEMO_TYPED = ["Explain BG 2.47"]


def read_chips() -> dict[str, str]:
    """label -> query for every chip/theme object in SuggestedChips.tsx."""
    src = CHIPS_TSX.read_text(encoding="utf-8")
    pairs = re.findall(
        r"label:\s*'((?:[^'\\]|\\.)*)'\s*,\s*query:\s*'((?:[^'\\]|\\.)*)'", src
    )
    return {
        label.replace("\\'", "'"): query.replace("\\'", "'") for label, query in pairs
    }


ap = argparse.ArgumentParser()
ap.add_argument("queries", nargs="*", help="extra typed queries to warm")
ap.add_argument("--base", default="http://localhost:8000", help="backend base URL")
ap.add_argument(
    "--gap", type=float, default=25.0, help="seconds between uncached requests"
)
ap.add_argument("--list", action="store_true", help="print the chip mapping and exit")
ap.add_argument(
    "--all-chips", action="store_true", help="warm every chip, not just the demo ones"
)
args = ap.parse_args()

chips = read_chips()
print(f"Chips in {CHIPS_TSX.name} (label -> query sent):")
for label, query in chips.items():
    mark = "*" if args.all_chips or label in DEMO_CHIP_LABELS else " "
    print(f" {mark} {label!r:<40} -> {query!r}")
if args.list:
    sys.exit(0)

missing = [lbl for lbl in DEMO_CHIP_LABELS if lbl not in chips]
if missing:
    print(f"WARNING: demo chip(s) not found in the frontend source: {missing}")
labels = (
    list(chips) if args.all_chips else [lbl for lbl in DEMO_CHIP_LABELS if lbl in chips]
)
queries = [chips[lbl] for lbl in labels] + DEMO_TYPED + args.queries
print(f"\nWarming {len(queries)} queries against {args.base}, {args.gap:.0f}s apart:\n")

failed = 0
with httpx.Client(base_url=args.base, timeout=120.0) as client:
    for i, q in enumerate(queries):
        t0 = time.perf_counter()
        try:
            r = client.post("/api/ask", json={"query": q, "top_k": 5, "multi": True})
        except httpx.HTTPError as e:
            print(
                f"[{i + 1}/{len(queries)}] request failed ({type(e).__name__}). Is the backend running?  {q!r}"
            )
            failed += 1
            continue
        dt = time.perf_counter() - t0
        cache = r.headers.get("X-VYOM-Cache", "-")
        words = len(r.json().get("answer", "").split()) if r.status_code == 200 else 0
        print(
            f"[{i + 1}/{len(queries)}] {r.status_code}  cache={cache:<4}  provider={r.headers.get('X-LLM-Provider', '-'):<7}"
            f"  model={r.headers.get('X-LLM-Model', '-')}  {dt:5.2f}s  {words} words  {q!r}"
        )
        if r.status_code != 200:
            failed += 1
        if (
            i < len(queries) - 1 and cache != "HIT"
        ):  # only wait after requests that spent Groq tokens
            time.sleep(args.gap)

sys.exit(1 if failed else 0)
