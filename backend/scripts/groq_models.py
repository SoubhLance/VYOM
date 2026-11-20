"""List the models this Groq key can access (GET /openai/v1/models, no generation). Never prints the key."""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # backend/.env; keys only from there
r = httpx.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
    timeout=30,
)
print("status:", r.status_code)
for m in sorted(r.json().get("data", []), key=lambda m: m["id"]):
    print(
        f"{m['id']:<50} owner={m.get('owned_by', '-'):<16} ctx={m.get('context_window', '-'):<8} "
        f"max_out={m.get('max_completion_tokens', '-'):<7} active={m.get('active', '-')}"
    )
