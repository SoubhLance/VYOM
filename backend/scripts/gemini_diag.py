"""Diagnose the Gemini 404: which models does this key see, and does the configured model answer?
Key goes in the x-goog-api-key header, never in the URL or output."""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # backend/.env; keys only from there
key = os.getenv("GEMINI_API_KEY")
configured = os.getenv("GEMINI_MODEL")
print("GEMINI_API_KEY present:", bool(key), "| GEMINI_MODEL in .env:", configured)
if not key:
    sys.exit(1)
H = {"x-goog-api-key": key}
BASE = "https://generativelanguage.googleapis.com/v1beta"

with httpx.Client(timeout=30) as c:
    r = c.get(f"{BASE}/models", headers=H, params={"pageSize": 200})
    print("list models:", r.status_code)
    if r.status_code == 200:
        names = [
            m["name"].split("/", 1)[1]
            for m in r.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        flash = [n for n in names if "flash" in n]
        print(
            f"{len(names)} models support generateContent; flash ones:",
            ", ".join(sorted(flash)),
        )
    else:
        print("error body:", r.text[:300])

    for model in dict.fromkeys(
        sys.argv[1:]
        or [configured, "gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    ):
        if not model:
            continue
        r = c.post(
            f"{BASE}/models/{model}:generateContent",
            headers=H,
            json={
                "contents": [
                    {"parts": [{"text": "Reply with exactly one word: ready"}]}
                ]
            },
        )
        msg = ""
        if r.status_code == 200:
            try:
                msg = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()[
                    :30
                ]
            except Exception:
                msg = "(no text)"
        else:
            msg = (
                r.json().get("error", {}).get("status", "")
                + ": "
                + r.json().get("error", {}).get("message", "")[:160]
            )
        print(f"generateContent {model}: {r.status_code} {msg!r}")
