"""LLM Client with configurable fallback chain:
Default order: Groq -> Google Gemini -> Ollama.
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

import google.generativeai as genai
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

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
# llama-3.3-70b-versatile is Enterprise-tier on Groq now and returns 404 on this account,
# so gpt-oss-120b is the default. Override with GROQ_MODEL.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# gpt-oss always reasons and its hidden reasoning tokens count toward max_tokens
# (measured 2026-11-11: 801 of 950). Keep effort low and leave room for the visible answer.
GPT_OSS_DEFAULT_REASONING_EFFORT = "low"
DEFAULT_GROQ_MAX_TOKENS = "1800"
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
OLLAMA_DEFAULT_MODEL = "llama3.2"
DEFAULT_TIMEOUT = 30.0

# Process-level state tracking
DEAD_PROVIDERS: set[str] = set()
RATE_LIMITED_PROVIDERS: dict[str, float] = {}
LAST_CALL_METADATA: dict[str, Any] = {
    "finish_reason": None,
    "provider": None,
    "model": None,
    "fallback_used": False,
    "prompt_tokens": None,
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


def get_last_fallback_used() -> bool:
    """Return True if a fallback path fired during the most recent LLM call."""
    return bool(LAST_CALL_METADATA.get("fallback_used", False))


def get_last_usage() -> dict[str, Any]:
    """Return token usage metadata from the most recent LLM completion call."""
    return {
        "prompt_tokens": LAST_CALL_METADATA.get("prompt_tokens"),
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


def _call_gemini(prompt: str, system_prompt: str, api_key: str) -> str:
    """Invoke Google Gemini using official google.generativeai SDK."""
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt if system_prompt else None,
        )
        try:
            response = model.generate_content(prompt, request_options={"timeout": DEFAULT_TIMEOUT})
        except TypeError:
            response = model.generate_content(prompt)
    except TypeError:
        # Fallback if system_instruction argument is not supported
        model = genai.GenerativeModel(model_name=model_name)
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        try:
            response = model.generate_content(full_prompt, request_options={"timeout": DEFAULT_TIMEOUT})
        except TypeError:
            response = model.generate_content(full_prompt)

    text = getattr(response, "text", "")
    if not text:
        raise ValueError(f"Empty or invalid response from Gemini: {response}")
    return text.strip()


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


def _call_groq(prompt: str, system_prompt: str, api_key: str, temperature: float = 0.2) -> tuple[str, str, bool]:
    """Invoke Groq using official groq SDK."""
    client = Groq(api_key=api_key, timeout=DEFAULT_TIMEOUT)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    model_name = os.getenv("GROQ_MODEL", GROQ_MODEL)
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
        LAST_CALL_METADATA["prompt_tokens"] = getattr(usage, "prompt_tokens", None)
        LAST_CALL_METADATA["completion_tokens"] = getattr(usage, "completion_tokens", None)
        LAST_CALL_METADATA["total_tokens"] = getattr(usage, "total_tokens", None)
        LAST_CALL_METADATA["completion_tokens_details"] = str(details) if details is not None else None
        LAST_CALL_METADATA["reasoning_tokens"] = reasoning_tokens
        logger.info(
            "Groq usage: prompt=%s, completion=%s, total=%s, details=%s, reasoning_tokens=%s",
            LAST_CALL_METADATA["prompt_tokens"],
            LAST_CALL_METADATA["completion_tokens"],
            LAST_CALL_METADATA["total_tokens"],
            details,
            reasoning_tokens,
        )
    else:
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


def _call_ollama(prompt: str, system_prompt: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Invoke local Ollama REST endpoint."""
    url = os.getenv("OLLAMA_URL", OLLAMA_DEFAULT_URL)
    model = os.getenv("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
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


def generate_answer(prompt: str, system_prompt: str = "", temperature: float = 0.2) -> str:
    """Generate answer following configurable fallback chain (default: groq,gemini,ollama)."""
    providers_str = os.getenv("LLM_PROVIDERS", "groq,gemini,ollama")
    provider_order = [p.strip().lower() for p in providers_str.split(",") if p.strip()]

    errors: list[str] = []
    now = time.time()

    for p in provider_order:
        # Check if provider is permanently dead (401/403/404)
        if p in DEAD_PROVIDERS:
            continue

        # Check if provider is rate-limited (429 cooldown 60s)
        if p in RATE_LIMITED_PROVIDERS:
            if now < RATE_LIMITED_PROVIDERS[p]:
                continue
            del RATE_LIMITED_PROVIDERS[p]

        # Skip provider if API key is missing
        api_key = None
        if p == "groq":
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

        try:
            fallback_fired = False
            if p == "groq":
                ans, actual_model, inner_fallback = _call_groq(prompt, system_prompt, api_key, temperature=temperature)
                fallback_fired = inner_fallback or (p != provider_order[0])
            elif p == "gemini":
                ans = _call_gemini(prompt, system_prompt, api_key)
                actual_model = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
                fallback_fired = (p != provider_order[0])
            elif p == "ollama":
                ans = _call_ollama(prompt, system_prompt)
                actual_model = os.getenv("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
                fallback_fired = (p != provider_order[0])
            else:
                continue

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
            if status_code is not None:
                logger.warning("Provider %s failed with status code %s", p, status_code)
                if status_code in (401, 403, 404):
                    DEAD_PROVIDERS.add(p)
                elif status_code == 429:
                    RATE_LIMITED_PROVIDERS[p] = time.time() + 60.0
                errors.append(f"{p} (status {status_code})")
            else:
                err_type = type(e).__name__
                logger.warning("Provider %s failed: %s", p, err_type)
                errors.append(f"{p} ({err_type})")

    raise RuntimeError(
        "All LLM generation providers in fallback chain failed:\n"
        + "\n".join(f"- {err}" for err in errors)
    )
