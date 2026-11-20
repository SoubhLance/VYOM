"""Force each LLM provider (and each fallback chain) in turn and report who answered and how fast.

    .\\venv\\python.exe backend\\scripts\\failover_check.py          # tiny prompt per chain (~100 Groq tokens)
    .\\venv\\python.exe backend\\scripts\\failover_check.py --ask    # also one /api/ask with Groq switched off
Never prints keys or raw error text (only exception type and HTTP status).
"""

import argparse
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from llm import client  # noqa: E402  (loads backend/.env)

CHAINS = [
    "groq",
    "groq2",
    "gemini",
    "ollama",
    "gemini,ollama",
    "groq,groq2,gemini,ollama",
]

ap = argparse.ArgumentParser()
ap.add_argument(
    "--ask",
    action="store_true",
    help="also send one real /api/ask with LLM_PROVIDERS=gemini,ollama",
)
args = ap.parse_args()

for chain in CHAINS:
    client.DEAD_PROVIDERS.clear()
    client.RATE_LIMITED_PROVIDERS.clear()
    os.environ["LLM_PROVIDERS"] = chain
    t0 = time.perf_counter()
    try:
        ans = client.generate_answer(
            "Reply with exactly one word: ready", system_prompt=""
        )
        print(
            f"{chain:<20} OK    provider={client.get_last_provider():<7} model={ans.model:<22} "
            f"{time.perf_counter() - t0:6.2f}s  answer={str(ans)[:20]!r}"
        )
    except RuntimeError as e:
        failures = "; ".join(line.strip("- ") for line in str(e).splitlines()[1:])
        print(f"{chain:<20} FAIL  {time.perf_counter() - t0:6.2f}s  {failures}")

if args.ask:
    from fastapi.testclient import TestClient

    from api.main import app

    client.DEAD_PROVIDERS.clear()
    client.RATE_LIMITED_PROVIDERS.clear()
    os.environ["LLM_PROVIDERS"] = "gemini,ollama"
    with TestClient(app) as c:
        t0 = time.perf_counter()
        r = c.post(
            "/api/ask",
            json={
                "query": "How does Sri Krishna advise mastering a turbulent mind in BG 6.35?",
                "top_k": 5,
                "multi": True,
            },
        )
        dt = time.perf_counter() - t0
        body = r.json()
        answer = str(body.get("answer", ""))
        print(
            f"\n/api/ask with LLM_PROVIDERS=gemini,ollama: HTTP {r.status_code} in {dt:.2f}s, "
            f"provider={r.headers.get('X-LLM-Provider', '-')}, model={r.headers.get('X-LLM-Model', '-')}"
        )
        if r.status_code == 200:
            import re as _re

            print(
                f"  words={len(answer.split())} citations={_re.findall(r'[(]BG[ ]*[0-9]+[.][0-9]+[)]', answer)} "
                f"warnings={body.get('warnings')}"
            )
            print(f"  answer head: {answer[:300]!r}")
        else:
            print(f"  body: {r.text[:200]}")
