import logging
import os
import sys
import time
from pathlib import Path

# Setup logging to capture log lines
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout
)

ROOT = Path("backend").resolve()
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from llm.client import (
    _call_groq,
    _call_mistral,
    _call_gemini,
    _call_ollama,
    generate_answer,
    _extract_status_code,
    DEAD_PROVIDERS,
    RATE_LIMITED_PROVIDERS
)

PROMPT = "Reply with the single word: ok"

print("=" * 70)
print("PART 1: DIRECT PROVIDER CALLS (at most 1 call per provider)")
print("=" * 70)

providers_to_test = [
    ("groq", _call_groq, os.getenv("GROQ_API_KEY")),
    ("mistral", _call_mistral, os.getenv("MISTRAL_API_KEY") or "deliberately_wrong_test_key"),
    ("gemini", _call_gemini, os.getenv("GEMINI_API_KEY")),
    ("ollama", lambda p, s, k: _call_ollama(p, s), None),
]

for name, func, key in providers_to_test:
    start_t = time.time()
    success = False
    status_or_err = "OK"
    resp_text = ""
    try:
        if name == "ollama":
            resp_text = func(PROMPT, "", None)
        else:
            if not key:
                raise ValueError("No API key configured")
            resp_text = func(PROMPT, "", key)
        success = True
        status_or_err = "200 (Success)"
    except Exception as e:
        sc = _extract_status_code(e)
        if sc:
            status_or_err = f"HTTP {sc}"
        else:
            status_or_err = type(e).__name__
    latency = time.time() - start_t

    status_str = "SUCCESS" if success else "FAILURE"
    print(f"Provider: {name:<10} | Result: {status_str:<7} | Code/Type: {status_or_err:<20} | Latency: {latency:.3f}s")
    if success:
        print(f"  Response: {repr(resp_text[:60])}")

print("\n" + "=" * 70)
print("PART 2: FALLBACK CHAIN TEST (LLM_PROVIDERS='mistral,groq' with invalid Mistral key)")
print("=" * 70)

os.environ["LLM_PROVIDERS"] = "mistral,groq"
os.environ["MISTRAL_API_KEY"] = "deliberately_wrong_mistral_key_abc123"

# Clear dead providers before testing the chain
DEAD_PROVIDERS.clear()
RATE_LIMITED_PROVIDERS.clear()

print("Calling generate_answer(PROMPT)...")
t0 = time.time()
ans = generate_answer(PROMPT)
dt = time.time() - t0

print(f"\nFinal answer returned: {repr(ans)}")
print(f"Chain latency: {dt:.3f}s")
print(f"Dead providers set: {DEAD_PROVIDERS}")

print("\nCalling generate_answer(PROMPT) a second time to verify Mistral is skipped immediately (no retry):")
t1 = time.time()
ans2 = generate_answer(PROMPT)
dt2 = time.time() - t1
print(f"Second call answer: {repr(ans2)}")
print(f"Second call latency: {dt2:.3f}s")

