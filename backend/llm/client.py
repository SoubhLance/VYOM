"""LLM Client with configurable fallback chain:
Default order: Groq (gpt-oss-120b) -> groq2 (gpt-oss-20b) -> Gemini (REST) -> Ollama.
Configured via LLM_PROVIDERS environment variable.
"""
import logging
import os
from pathlib import Path
import re
import time
from typing import Any
import httpx
from dotenv import load_dotenv

from groq import Groq

# Load environment variables from backend/.env or root .env
_backend_dir = Path(__file__).resolve().parents[1]
_env_backend = _backend_dir / ".env"
_env_root = _backend_dir.parent / ".env"
if _env_backend.exists():
    load_dotenv(dotenv_path=_env_backend)
elif _env_root.exists():
    load_dotenv(dotenv_path=_env_root)
else:
    load_dotenv()

logger = logging.getLogger(__name__)

# gemini-2.5-flash / -lite return 404 "no longer available to new users" (2026-11-19); 3.5-flash-lite answers.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MAX_TOKENS = 2048
# Second Groq tier: Groq rate limits are per model, so a 429 on gpt-oss-120b can fall to gpt-oss-20b.
GROQ_FALLBACK_MODEL = "openai/gpt-oss-20b"
# llama-3.3-70b-versatile is Enterprise-tier on Groq now and returns 404 on this account,
# so gpt-oss-120b is the default. Override with GROQ_MODEL.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# gpt-oss always reasons and its hidden reasoning tokens count toward max_tokens
# (measured 2026-11-11: 801 of 950). Keep effort low and leave room for the visible answer.
GPT_OSS_DEFAULT_REASONING_EFFORT = "low"
DEFAULT_GROQ_MAX_TOKENS = "1000"  # observed 147-503 completion tokens (2026-11-19)
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
OLLAMA_DEFAULT_MODEL = "llama3.2"
# The v2 prompt is ~2-3K tokens; Ollama's default context window can be smaller and truncates silently.
OLLAMA_DEFAULT_NUM_CTX = 8192
# A local model may need to load into VRAM first, so allow longer than the cloud timeout.
OLLAMA_DEFAULT_TIMEOUT = 120.0
DEFAULT_TIMEOUT = 30.0
DEFAULT_LLM_PROVIDERS = "groq,groq2,gemini,ollama"
# 429 handling: SDK retries are off (max_retries=0) so a 429 reaches generate_answer at once.
# Retry once inline only when retry-after is short; otherwise cool the provider down and fail over.
RATE_LIMIT_MAX_INLINE_WAIT = 5.0
RATE_LIMIT_DEFAULT_COOLDOWN = 10.0

# Process-level state tracking
DEAD_PROVIDERS: set[str] = set()
RATE_LIMITED_PROVIDERS: dict[str, float] = {}
LAST_CALL_METADATA: dict[str, Any] = {
    "finish_reason": None,
    "provider": None,
    "model": None,
    "fallback_used": False,
    "prompt_tokens": None,
    "cached_tokens": None,
    "completion_tokens": None,
    "total_tokens": None,
    "reasoning_tokens": None,
    "completion_tokens_details": None,
    "visible_word_count": None,
}


class GenerationResult(str):
    """String subclass containing LLM completion metadata."""
    model: str | None = None
    fallback_used: bool = False
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None


def get_last_finish_reason() -> str | None:
    """Return the finish_reason of the most recent LLM completion call."""
    return LAST_CALL_METADATA.get("finish_reason")


def get_last_model() -> str | None:
    """Return the model that actually answered the most recent LLM call."""
    return LAST_CALL_METADATA.get("model")


def get_last_provider() -> str | None:
    """Return the provider (groq / gemini / ollama) that answered the most recent LLM call."""
    return LAST_CALL_METADATA.get("provider")


def get_last_fallback_used() -> bool:
    """Return True if a fallback path fired during the most recent LLM call."""
    return bool(LAST_CALL_METADATA.get("fallback_used", False))


def get_last_usage() -> dict[str, Any]:
    """Return token usage metadata from the most recent LLM completion call."""
    return {
        "prompt_tokens": LAST_CALL_METADATA.get("prompt_tokens"),
        "cached_tokens": LAST_CALL_METADATA.get("cached_tokens"),
        "completion_tokens": LAST_CALL_METADATA.get("completion_tokens"),
        "total_tokens": LAST_CALL_METADATA.get("total_tokens"),
        "reasoning_tokens": LAST_CALL_METADATA.get("reasoning_tokens"),
        "completion_tokens_details": LAST_CALL_METADATA.get("completion_tokens_details"),
        "visible_word_count": LAST_CALL_METADATA.get("visible_word_count"),
    }


def are_quotes_balanced(s: str) -> bool:
    """Check if straight quotes, curly quotes, and parentheses are balanced."""
    if s.count('"') % 2 != 0:
        return False
    if s.count('“') != s.count('”'):
        return False
    if s.count('(') != s.count(')'):
        return False
    return True


def clean_truncated_answer(text: str) -> str:
    """On finish_reason == 'length', cut the answer back to the last complete sentence
    or paragraph before appending '(answer shortened)'. Never leave an unclosed quote mark."""
    stripped = text.strip()
    if not stripped:
        return ""

    # Look for candidate sentence boundaries:
    # 1. Punctuation [.!?] followed by optional quotes/parens
    # 2. Citation (BG x.y) followed by optional punctuation
    boundary_pattern = re.compile(
        r'(?:(?<!\d)[.!?]["”\'\)\]]*|\((?:BG\s*)?[0-9]{1,2}\.[0-9]{1,2}\)[.!?]?)',
        re.IGNORECASE
    )

    matches = list(boundary_pattern.finditer(stripped))

    # Scan backwards from the last match
    best_cutoff = None
    for m in reversed(matches):
        candidate_end = m.end()
        candidate_text = stripped[:candidate_end].rstrip()
        if are_quotes_balanced(candidate_text):
            best_cutoff = candidate_end
            break

    if best_cutoff is not None:
        trimmed = stripped[:best_cutoff].rstrip()
    else:
        # Fallback: check paragraphs if no balanced punctuation found
        paragraphs = stripped.split("\n\n")
        trimmed = ""
        for p in paragraphs:
            candidate = (trimmed + "\n\n" + p).strip() if trimmed else p.strip()
            if are_quotes_balanced(candidate):
                trimmed = candidate
            else:
                break
        if not trimmed:
            trimmed = stripped

    # Ensure no unclosed quote remains at the very end
    while trimmed and not are_quotes_balanced(trimmed):
        trimmed = re.sub(r'[\s\S]$', '', trimmed).rstrip()

    # No visible label: callers report truncation through the "truncated" warning.
    return trimmed


def _extract_status_code(e: Exception) -> int | None:
    """Extract HTTP status code from an exception if available."""
    if hasattr(e, "status_code") and isinstance(e.status_code, int):
        return e.status_code
    if hasattr(e, "response") and hasattr(e.response, "status_code") and isinstance(e.response.status_code, int):
        return e.response.status_code
    if hasattr(e, "code") and isinstance(e.code, int):
        return e.code
    m = re.search(r"\b(40[0-9]|4[1-9][0-9]|5[0-9]{2})\b", str(e))
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def _call_gemini(prompt: str, system_prompt: str, api_key: str, temperature: float = 0.2) -> str:
    """Invoke Gemini generateContent over plain REST. The key goes in a header, never in the URL.
    Non-2xx responses raise httpx.HTTPStatusError, so generate_answer sees the status code."""
    model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": int(os.getenv("GEMINI_MAX_TOKENS", str(DEFAULT_GEMINI_MAX_TOKENS))),
        },
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            f"{GEMINI_API_BASE}/models/{model_name}:generateContent",
            headers={"x-goog-api-key": api_key},
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates") or []
    parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
    text = "".join(str(p.get("text", "")) for p in parts if not p.get("thought")).strip()
    if not text:
        raise ValueError("Empty response from Gemini")
    finish = str(candidates[0].get("finishReason", "")).upper()
    usage = data.get("usageMetadata") or {}
    LAST_CALL_METADATA["finish_reason"] = "length" if finish == "MAX_TOKENS" else "stop"
    LAST_CALL_METADATA["prompt_tokens"] = usage.get("promptTokenCount")
    LAST_CALL_METADATA["cached_tokens"] = usage.get("cachedContentTokenCount")
    LAST_CALL_METADATA["completion_tokens"] = usage.get("candidatesTokenCount")
    LAST_CALL_METADATA["reasoning_tokens"] = usage.get("thoughtsTokenCount")
    LAST_CALL_METADATA["total_tokens"] = usage.get("totalTokenCount")
    if LAST_CALL_METADATA["finish_reason"] == "length":
        text = clean_truncated_answer(text)
    return text


def _apply_reasoning_settings(kwargs: dict[str, Any]) -> None:
    """Set reasoning parameters for the model in kwargs["model"].

    gpt-oss models (every Groq call: answers and the LLM splitter) get reasoning_effort
    (GROQ_REASONING_EFFORT, default "low") and include_reasoning=False so the reasoning text is
    not returned. Other models only get reasoning_effort when GROQ_REASONING_EFFORT is set.
    """
    env_effort = (os.getenv("GROQ_REASONING_EFFORT") or "").strip()
    if str(kwargs.get("model", "")).startswith("openai/gpt-oss"):
        kwargs["reasoning_effort"] = env_effort or GPT_OSS_DEFAULT_REASONING_EFFORT
        kwargs["include_reasoning"] = False
    elif env_effort:
        kwargs["reasoning_effort"] = env_effort


_GROQ_CLIENTS: dict[tuple[int, str], Any] = {}


def _groq_client(api_key: str) -> Any:
    """One Groq client per key, reused across calls so its HTTP connection stays open.
    Keyed on the Groq class too, so a patched class in tests gets its own instance."""
    k = (id(Groq), api_key)
    if k not in _GROQ_CLIENTS:
        _GROQ_CLIENTS[k] = Groq(api_key=api_key, timeout=DEFAULT_TIMEOUT, max_retries=0)
    return _GROQ_CLIENTS[k]


def _call_groq(
    prompt: str, system_prompt: str, api_key: str, temperature: float = 0.2, model: str | None = None
) -> tuple[str, str, bool]:
    """Invoke Groq using official groq SDK."""
    client = _groq_client(api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    model_name = model or os.getenv("GROQ_MODEL", GROQ_MODEL)
    max_tokens = int(os.getenv("GROQ_MAX_TOKENS", DEFAULT_GROQ_MAX_TOKENS))
    kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    _apply_reasoning_settings(kwargs)

    model_fallback_fired = False
    try:
        completion = client.chat.completions.create(**kwargs)
    except Exception as e:
        # If default llama-3.3-70b-versatile is not accessible on the account, fallback to active model
        if "model_not_found" in str(e).lower() and model_name != "openai/gpt-oss-120b":
            logger.warning("Groq model %s not found; falling back to openai/gpt-oss-120b", model_name)
            kwargs["model"] = "openai/gpt-oss-120b"
            kwargs.pop("reasoning_effort", None)
            kwargs.pop("include_reasoning", None)
            _apply_reasoning_settings(kwargs)
            completion = client.chat.completions.create(**kwargs)
            model_fallback_fired = True
        else:
            raise e

    choices = completion.choices
    if not choices or not choices[0].message or not choices[0].message.content:
        raise ValueError(f"No text content returned from Groq completion: {completion}")
    finish_reason = getattr(choices[0], "finish_reason", "unknown")
    actual_model = getattr(completion, "model", kwargs["model"])
    LAST_CALL_METADATA["finish_reason"] = finish_reason
    LAST_CALL_METADATA["provider"] = "groq"
    LAST_CALL_METADATA["model"] = actual_model
    LAST_CALL_METADATA["fallback_used"] = model_fallback_fired

    # Capture token usage and reasoning details from Groq completion
    usage = getattr(completion, "usage", None)
    details = getattr(usage, "completion_tokens_details", None) if usage else None
    reasoning_tokens = None
    if details is not None:
        if hasattr(details, "reasoning_tokens"):
            reasoning_tokens = details.reasoning_tokens
        elif isinstance(details, dict):
            reasoning_tokens = details.get("reasoning_tokens")

    if usage:
        ptd = getattr(usage, "prompt_tokens_details", None)
        cached = getattr(ptd, "cached_tokens", None) if ptd is not None else None
        LAST_CALL_METADATA["cached_tokens"] = cached if isinstance(cached, int) else None
        LAST_CALL_METADATA["prompt_tokens"] = getattr(usage, "prompt_tokens", None)
        LAST_CALL_METADATA["completion_tokens"] = getattr(usage, "completion_tokens", None)
        LAST_CALL_METADATA["total_tokens"] = getattr(usage, "total_tokens", None)
        LAST_CALL_METADATA["completion_tokens_details"] = str(details) if details is not None else None
        LAST_CALL_METADATA["reasoning_tokens"] = reasoning_tokens
        logger.info(
            "Groq usage: prompt=%s, cached=%s, completion=%s, total=%s, details=%s, reasoning_tokens=%s",
            LAST_CALL_METADATA["prompt_tokens"],
            LAST_CALL_METADATA["cached_tokens"],
            LAST_CALL_METADATA["completion_tokens"],
            LAST_CALL_METADATA["total_tokens"],
            details,
            reasoning_tokens,
        )
    else:
        LAST_CALL_METADATA["cached_tokens"] = None
        LAST_CALL_METADATA["prompt_tokens"] = None
        LAST_CALL_METADATA["completion_tokens"] = None
        LAST_CALL_METADATA["total_tokens"] = None
        LAST_CALL_METADATA["completion_tokens_details"] = None
        LAST_CALL_METADATA["reasoning_tokens"] = None

    logger.info("Groq completion finish_reason: %s (model: %s)", finish_reason, actual_model)
    ans = choices[0].message.content.strip()
    visible_word_count = len(ans.split())
    LAST_CALL_METADATA["visible_word_count"] = visible_word_count
    logger.info("Visible answer word count: %d", visible_word_count)

    if finish_reason == "length":
        ans = clean_truncated_answer(ans)
    return ans, actual_model, model_fallback_fired


def _call_ollama(prompt: str, system_prompt: str, timeout: float | None = None) -> str:
    """Invoke local Ollama REST endpoint."""
    url = os.getenv("OLLAMA_URL", OLLAMA_DEFAULT_URL)
    model = os.getenv("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": int(os.getenv("OLLAMA_NUM_CTX", str(OLLAMA_DEFAULT_NUM_CTX)))},
    }
    if timeout is None:
        timeout = float(os.getenv("OLLAMA_TIMEOUT", str(OLLAMA_DEFAULT_TIMEOUT)))
    if system_prompt:
        payload["system"] = system_prompt

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        ans = data.get("response", "")
        if not ans and "error" in data:
            raise ValueError(f"Ollama returned error: {data['error']}")
        return ans.strip()


def _retry_after_seconds(e: Exception) -> float | None:
    """Seconds from a 429's retry-after header, or None when the header is missing or not numeric."""
    resp = getattr(e, "response", None)
    headers = getattr(resp, "headers", None)
    if not headers:
        return None
    try:
        raw = headers.get("retry-after")
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return max(0.0, float(str(raw).strip()))
    except ValueError:
        return None


def _call_provider(p: str, prompt: str, system_prompt: str, api_key: str | None, temperature: float) -> tuple[str, str, bool]:
    """Call one provider. Returns (answer, model, inner_model_fallback)."""
    if p == "groq":
        return _call_groq(prompt, system_prompt, api_key, temperature=temperature)
    if p == "groq2":
        return _call_groq(
            prompt, system_prompt, api_key, temperature=temperature,
            model=os.getenv("GROQ_FALLBACK_MODEL", GROQ_FALLBACK_MODEL),
        )
    if p == "gemini":
        ans = _call_gemini(prompt, system_prompt, api_key, temperature=temperature)
        return ans, os.getenv("GEMINI_MODEL", GEMINI_MODEL), False
    ans = _call_ollama(prompt, system_prompt)
    LAST_CALL_METADATA["finish_reason"] = None
    return ans, os.getenv("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL), False


def generate_answer(prompt: str, system_prompt: str = "", temperature: float = 0.2) -> str:
    """Generate answer following configurable fallback chain (default: groq,gemini,ollama).

    429: one inline retry when retry-after <= RATE_LIMIT_MAX_INLINE_WAIT seconds; otherwise the provider
    cools down for retry-after (or RATE_LIMIT_DEFAULT_COOLDOWN when missing) and the next provider is tried.
    401/403/404 mark the provider dead for the life of the process.
    """
    providers_str = os.getenv("LLM_PROVIDERS", DEFAULT_LLM_PROVIDERS)
    provider_order = [p.strip().lower() for p in providers_str.split(",") if p.strip()]

    errors: list[str] = []

    for p in provider_order:
        # Check if provider is permanently dead (401/403/404)
        if p in DEAD_PROVIDERS:
            continue

        # Skip provider while its rate-limit cooldown runs
        if p in RATE_LIMITED_PROVIDERS:
            if time.time() < RATE_LIMITED_PROVIDERS[p]:
                logger.info("Provider %s skipped: rate-limit cooldown %.1fs left", p, RATE_LIMITED_PROVIDERS[p] - time.time())
                continue
            del RATE_LIMITED_PROVIDERS[p]

        # Skip provider if API key is missing
        api_key = None
        if p in ("groq", "groq2"):
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                continue
        elif p == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                continue
        elif p == "ollama":
            pass
        else:
            continue

        retried = False
        while True:
            try:
                ans, actual_model, inner_fallback = _call_provider(p, prompt, system_prompt, api_key, temperature)
                fallback_fired = inner_fallback or (p != provider_order[0])

                LAST_CALL_METADATA["provider"] = p
                LAST_CALL_METADATA["model"] = actual_model
                LAST_CALL_METADATA["fallback_used"] = fallback_fired
                logger.info("Provider %s answered (model: %s, fallback: %s)", p, actual_model, fallback_fired)

                res = GenerationResult(ans)
                res.model = actual_model
                res.fallback_used = fallback_fired
                res.finish_reason = LAST_CALL_METADATA.get("finish_reason")
                res.prompt_tokens = LAST_CALL_METADATA.get("prompt_tokens")
                res.completion_tokens = LAST_CALL_METADATA.get("completion_tokens")
                res.total_tokens = LAST_CALL_METADATA.get("total_tokens")
                res.reasoning_tokens = LAST_CALL_METADATA.get("reasoning_tokens")
                return res
            except Exception as e:
                status_code = _extract_status_code(e)
                if status_code == 429:
                    retry_after = _retry_after_seconds(e)
                    if not retried and retry_after is not None and retry_after <= RATE_LIMIT_MAX_INLINE_WAIT:
                        logger.warning("RATE_LIMITED provider=%s retry_after=%.1fs: retrying once", p, retry_after)
                        retried = True
                        time.sleep(retry_after)
                        continue
                    cooldown = retry_after if retry_after is not None else RATE_LIMIT_DEFAULT_COOLDOWN
                    RATE_LIMITED_PROVIDERS[p] = time.time() + cooldown
                    logger.warning(
                        "RATE_LIMITED provider=%s retry_after=%s: cooling down %.1fs, failing over",
                        p, retry_after, cooldown,
                    )
                    errors.append(f"{p} (status 429)")
                elif status_code is not None:
                    logger.warning("Provider %s failed with status code %s", p, status_code)
                    if status_code in (401, 403, 404):
                        DEAD_PROVIDERS.add(p)
                    errors.append(f"{p} (status {status_code})")
                else:
                    err_type = type(e).__name__
                    logger.warning("Provider %s failed: %s", p, err_type)
                    errors.append(f"{p} ({err_type})")
                break

    raise RuntimeError(
        "All LLM generation providers in fallback chain failed:\n"
        + "\n".join(f"- {err}" for err in errors)
    )
