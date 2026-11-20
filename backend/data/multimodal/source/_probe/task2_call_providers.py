import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment is reloaded from backend/.env
env_path = Path("backend/.env").resolve()
load_dotenv(dotenv_path=env_path, override=True)

ROOT = Path("backend").resolve()
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from llm.client import (
    _call_groq,
    _call_mistral,
    _call_gemini,
    _call_ollama,
    _extract_status_code,
    _CACHED_MISTRAL_MODEL
)
import llm.client as client_module

PROMPT = "Reply with the single word: ok"

print("=" * 70)
print("CALLING EACH PROVIDER FUNCTION DIRECTLY (1 call each)")
print(f"PROMPT: {repr(PROMPT)}")
print("=" * 70)

# 1. Groq
print("\n--- 1. Groq ---")
groq_key = os.getenv("GROQ_API_KEY")
t0 = time.time()
try:
    if not groq_key:
        raise ValueError("GROQ_API_KEY is not set")
    resp_groq = _call_groq(PROMPT, "", groq_key)
    lat_groq = time.time() - t0
    print(f"Provider:    groq")
    print(f"Result:      SUCCESS")
    print(f"Status/Type: HTTP 200 (OK)")
    print(f"Latency:     {lat_groq:.3f}s")
    print(f"Response:    {repr(resp_groq)}")
except Exception as e:
    lat_groq = time.time() - t0
    sc = _extract_status_code(e)
    print(f"Provider:    groq")
    print(f"Result:      FAILURE")
    print(f"Status/Type: {f'HTTP {sc}' if sc else type(e).__name__}")
    print(f"Latency:     {lat_groq:.3f}s")

# 2. Mistral
print("\n--- 2. Mistral ---")
mistral_key = os.getenv("MISTRAL_API_KEY")
t0 = time.time()
mistral_discovered_model = None
try:
    if not mistral_key:
        raise ValueError("MISTRAL_API_KEY is not set")
    resp_mistral = _call_mistral(PROMPT, "", mistral_key)
    lat_mistral = time.time() - t0
    mistral_discovered_model = client_module._CACHED_MISTRAL_MODEL or os.getenv("MISTRAL_MODEL")
    print(f"Provider:         mistral")
    print(f"Result:           SUCCESS")
    print(f"Status/Type:      HTTP 200 (OK)")
    print(f"Latency:          {lat_mistral:.3f}s")
    print(f"Discovered Model: {mistral_discovered_model}")
    print(f"Response:         {repr(resp_mistral)}")
except Exception as e:
    lat_mistral = time.time() - t0
    sc = _extract_status_code(e)
    mistral_discovered_model = client_module._CACHED_MISTRAL_MODEL or os.getenv("MISTRAL_MODEL")
    print(f"Provider:         mistral")
    print(f"Result:           FAILURE")
    print(f"Status/Type:      {f'HTTP {sc}' if sc else type(e).__name__}")
    print(f"Latency:          {lat_mistral:.3f}s")
    if mistral_discovered_model:
        print(f"Discovered Model: {mistral_discovered_model}")
    # If Mistral fails, print HTTP status code and response body's "message" field only
    if hasattr(e, "response") and e.response is not None:
        try:
            body = e.response.json()
            msg = None
            if isinstance(body, dict):
                msg = body.get("message")
                if not msg and "error" in body and isinstance(body["error"], dict):
                    msg = body["error"].get("message")
            if not msg:
                msg = str(body)
            print(f"Error Message:    {msg}")
        except Exception:
            print(f"Error Message:    {e.response.text}")

# 3. Gemini
print("\n--- 3. Gemini ---")
gemini_key = os.getenv("GEMINI_API_KEY")
t0 = time.time()
try:
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is not set")
    resp_gemini = _call_gemini(PROMPT, "", gemini_key)
    lat_gemini = time.time() - t0
    print(f"Provider:    gemini")
    print(f"Result:      SUCCESS")
    print(f"Status/Type: HTTP 200 (OK)")
    print(f"Latency:     {lat_gemini:.3f}s")
    print(f"Response:    {repr(resp_gemini)}")
except Exception as e:
    lat_gemini = time.time() - t0
    sc = _extract_status_code(e)
    print(f"Provider:    gemini")
    print(f"Result:      FAILURE")
    print(f"Status/Type: {f'HTTP {sc}' if sc else type(e).__name__}")
    print(f"Latency:     {lat_gemini:.3f}s")

# 4. Ollama
print("\n--- 4. Ollama ---")
t0 = time.time()
try:
    resp_ollama = _call_ollama(PROMPT, "")
    lat_ollama = time.time() - t0
    print(f"Provider:    ollama")
    print(f"Result:      SUCCESS")
    print(f"Status/Type: HTTP 200 (OK)")
    print(f"Latency:     {lat_ollama:.3f}s")
    print(f"Response:    {repr(resp_ollama)}")
except Exception as e:
    lat_ollama = time.time() - t0
    sc = _extract_status_code(e)
    print(f"Provider:    ollama")
    print(f"Result:      FAILURE")
    print(f"Status/Type: {f'HTTP {sc}' if sc else type(e).__name__}")
    print(f"Latency:     {lat_ollama:.3f}s")

