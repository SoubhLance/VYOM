"""LLM Client with graceful fallback chain:
1. Google Generative AI (gemini-1.5-flash) via GEMINI_API_KEY and google.generativeai SDK
2. Groq (llama-3.3-70b-versatile) via GROQ_API_KEY and groq SDK
3. Ollama (http://localhost:11434/api/generate)
"""
import logging
import os
from pathlib import Path
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
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
OLLAMA_DEFAULT_MODEL = "llama3.2"
DEFAULT_TIMEOUT = 30.0


def _call_gemini(prompt: str, system_prompt: str, api_key: str) -> str:
    """Invoke Google Gemini using official google.generativeai SDK."""
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt if system_prompt else None,
        )
        response = model.generate_content(prompt)
    except TypeError:
        # Fallback if system_instruction argument is not supported
        model = genai.GenerativeModel(model_name=model_name)
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = model.generate_content(full_prompt)

    text = getattr(response, "text", "")
    if not text:
        raise ValueError(f"Empty or invalid response from Gemini: {response}")
    return text.strip()


def _call_groq(prompt: str, system_prompt: str, api_key: str) -> str:
    """Invoke Groq using official groq SDK."""
    client = Groq(api_key=api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    model_name = os.getenv("GROQ_MODEL", GROQ_MODEL)
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.3,
        )
    except Exception as e:
        # If default llama-3.3-70b-versatile is not accessible on the account, fallback to active model
        if "model_not_found" in str(e).lower() and model_name != "openai/gpt-oss-120b":
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.3,
            )
        else:
            raise e

    choices = completion.choices
    if not choices or not choices[0].message or not choices[0].message.content:
        raise ValueError(f"No text content returned from Groq completion: {completion}")
    return choices[0].message.content.strip()


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


def generate_answer(prompt: str, system_prompt: str = "") -> str:
    """Generate answer following fallback chain:
    Google Generative AI (gemini-1.5-flash) -> Groq (llama-3.3-70b-versatile) -> Ollama (http://localhost:11434/api/generate).
    """
    errors = []

    # 1. Google Generative AI (gemini-1.5-flash)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            return _call_gemini(prompt, system_prompt, gemini_key)
        except Exception as e:
            msg = f"Google Generative AI ({GEMINI_MODEL}) failed: {e}"
            logger.warning(msg)
            errors.append(msg)
    else:
        errors.append("Google Generative AI skipped: GEMINI_API_KEY environment variable is not set")

    # 2. Groq (llama-3.3-70b-versatile)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            return _call_groq(prompt, system_prompt, groq_key)
        except Exception as e:
            msg = f"Groq ({GROQ_MODEL}) failed: {e}"
            logger.warning(msg)
            errors.append(msg)
    else:
        errors.append("Groq skipped: GROQ_API_KEY environment variable is not set")

    # 3. Ollama (http://localhost:11434/api/generate)
    try:
        return _call_ollama(prompt, system_prompt)
    except Exception as e:
        msg = f"Ollama ({OLLAMA_DEFAULT_URL}) failed: {e}"
        logger.warning(msg)
        errors.append(msg)

    raise RuntimeError(
        "All LLM generation providers in fallback chain failed:\n"
        + "\n".join(f"- {err}" for err in errors)
    )
