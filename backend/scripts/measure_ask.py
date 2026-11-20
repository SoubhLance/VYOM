"""Send real /api/ask requests in-process (real retrieval + real Groq) and record Groq usage.

Usage (repo root):
    .\\venv\\python.exe backend\\scripts\\measure_ask.py --gap 0 "q1" "q2" ...
Prints per request: HTTP status, latency, cache header, and every Groq call's prompt / cached /
completion / reasoning tokens. Never prints keys.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from groq.resources.chat import completions as groq_completions  # noqa: E402

CALLS: list[dict] = []
_orig_create = groq_completions.Completions.create


def _recording_create(self, *args, **kwargs):
    t0 = time.perf_counter()
    try:
        out = _orig_create(self, *args, **kwargs)
    except Exception as e:
        CALLS.append(
            {
                "error": type(e).__name__,
                "status": getattr(e, "status_code", None),
                "secs": round(time.perf_counter() - t0, 2),
            }
        )
        raise
    u = out.usage
    ptd = getattr(u, "prompt_tokens_details", None)
    ctd = getattr(u, "completion_tokens_details", None)
    CALLS.append(
        {
            "prompt": u.prompt_tokens,
            "cached": getattr(ptd, "cached_tokens", None) if ptd else None,
            "completion": u.completion_tokens,
            "reasoning": getattr(ctd, "reasoning_tokens", None) if ctd else None,
            "finish": out.choices[0].finish_reason,
            "groq_timing": {k: getattr(u, k, None) for k in ("queue_time", "prompt_time", "completion_time", "total_time")},
            "usage_keys": sorted(
                (u.model_dump() if hasattr(u, "model_dump") else {}).keys()
            ),
            "usage_extra": {
                k: v
                for k, v in (u.model_dump() if hasattr(u, "model_dump") else {}).items()
                if "cache" in k or "details" in k
            },
            "secs": round(time.perf_counter() - t0, 2),
        }
    )
    return out


groq_completions.Completions.create = _recording_create

from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("queries", nargs="+")
ap.add_argument(
    "--gap", type=float, default=0.0, help="seconds to wait between requests"
)
args = ap.parse_args()

results = []
with TestClient(app) as c:
    for i, q in enumerate(args.queries):
        if i and args.gap:
            time.sleep(args.gap)
        CALLS.clear()
        t0 = time.perf_counter()
        r = c.post("/api/ask", json={"query": q, "top_k": 5, "multi": True})
        dt = time.perf_counter() - t0
        body = (
            r.json()
            if r.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        row = {
            "query": q,
            "status": r.status_code,
            "latency_s": round(dt, 2),
            "cache": r.headers.get("X-VYOM-Cache"),
            "model": r.headers.get("X-LLM-Model"),
            "provider": r.headers.get("X-LLM-Provider"),
            "groq_calls": list(CALLS),
            "answer_words": len(str(body.get("answer", "")).split()),
            "warnings": body.get("warnings"),
            "citations": __import__("re").findall(r"\(BG\s*\d{1,2}\.\d{1,3}\)", str(body.get("answer", ""))),
            "answer_head": str(body.get("answer", ""))[:300],
            "n_sources": len(body.get("sources", []) or []),
        }
        results.append(row)
        print(json.dumps(row, ensure_ascii=False))
