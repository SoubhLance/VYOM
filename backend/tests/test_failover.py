"""Phase 2 (2026-11-19): Ollama call settings, and the quote verifier runs whichever provider answers."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import app
from llm import client

T_626 = "Restrain the restless and unsteady mind and bring it back under the control of the Self alone."


@pytest.fixture
def clean_providers():
    client.DEAD_PROVIDERS.clear()
    client.RATE_LIMITED_PROVIDERS.clear()
    yield
    client.DEAD_PROVIDERS.clear()
    client.RATE_LIMITED_PROVIDERS.clear()


def test_ollama_payload_sets_context_window_and_long_timeout():
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("llm.client.httpx.Client") as cls,
    ):
        http = cls.return_value.__enter__.return_value
        http.post.return_value.json.return_value = {"response": " local answer "}
        assert client._call_ollama("p", "s") == "local answer"
    cls.assert_called_once_with(timeout=client.OLLAMA_DEFAULT_TIMEOUT)
    payload = http.post.call_args.kwargs["json"]
    assert payload["options"]["num_ctx"] == client.OLLAMA_DEFAULT_NUM_CTX
    assert payload["system"] == "s" and payload["stream"] is False


def test_dead_gemini_falls_through_to_ollama(clean_providers):
    err = Exception("403 PERMISSION_DENIED free tier is not available")
    env = {"LLM_PROVIDERS": "gemini,ollama", "GEMINI_API_KEY": "k"}
    with (
        patch.dict(os.environ, env, clear=True),
        patch("llm.client._call_gemini", side_effect=err) as g,
        patch("llm.client._call_ollama", return_value="local") as o,
    ):
        assert client.generate_answer("q", "s") == "local"
        assert client.generate_answer("q", "s") == "local"
    assert (
        g.call_count == 1
    )  # 403 marks Gemini dead: the second call goes straight to Ollama
    assert o.call_count == 2 and "gemini" in client.DEAD_PROVIDERS
    assert client.get_last_provider() == "ollama"


@pytest.mark.parametrize("provider", ["groq2", "gemini", "ollama"])
def test_quote_verifier_runs_on_non_groq_answers(provider):
    """A fabricated quote from a fallback provider is removed exactly as for Groq."""
    searcher = MagicMock()
    searcher.search.return_value = [
        {"verse_id": "6.26", "score": 0.9, "chunks": [("6.26:v", 0.9)]}
    ]
    app.state.searcher = searcher
    app.state.valid_ids = {"6.26"}
    app.state.verse_store = {
        "6.26": {
            "verse_id": "6.26",
            "translations": {"english": [{"author": "Swami Sivananda", "text": T_626}]},
        }
    }
    fake = client.GenerationResult(
        "The mind is brought back to the Self (BG 6.26). "
        "Krishna also says “the mind must be crushed by fasting for forty days and nights” (BG 6.26)."
    )
    fake.model = "local-model"
    fake.fallback_used = True
    with (
        patch("api.main.generate_answer", return_value=fake),
        patch("api.main.get_last_provider", return_value=provider),
        patch("api.main.get_last_fallback_used", return_value=True),
        patch("api.main.get_last_finish_reason", return_value=None),
    ):
        r = TestClient(app).post(
            "/api/ask", json={"query": "How to master an agitated mind?", "multi": True}
        )
    body = r.json()
    assert r.status_code == 200
    assert "forty days" not in body["answer"]
    assert body["warnings"], "verifier should report the removed or replaced quote"
    assert (
        r.headers["X-LLM-Provider"] == provider and r.headers["X-VYOM-Cache"] == "MISS"
    )


def test_default_chain_order():
    assert client.DEFAULT_LLM_PROVIDERS == "groq,groq2,gemini,ollama"


class _RateLimit(Exception):
    status_code = 429

    def __init__(self):
        super().__init__("Error code: 429")
        self.response = SimpleNamespace(headers={"retry-after": "40"})


def test_groq_429_falls_to_groq2_with_fallback_model(clean_providers):
    env = {"GROQ_API_KEY": "k"}
    calls = []

    def fake_groq(prompt, system_prompt, api_key, temperature=0.2, model=None):
        calls.append(model)
        if model is None:
            raise _RateLimit()
        return "small model answer", model, False

    with (
        patch.dict(os.environ, env, clear=True),
        patch("llm.client._call_groq", side_effect=fake_groq),
        patch("llm.client._call_gemini") as g,
        patch("llm.client.time.sleep") as sleep,
    ):
        ans = client.generate_answer("q", "s")
    assert ans == "small model answer" and ans.model == "openai/gpt-oss-20b"
    assert calls == [None, "openai/gpt-oss-20b"]
    assert client.get_last_provider() == "groq2" and ans.fallback_used is True
    assert "groq" in client.RATE_LIMITED_PROVIDERS and "groq2" not in client.RATE_LIMITED_PROVIDERS
    g.assert_not_called()  # no GEMINI_API_KEY in this env
    sleep.assert_not_called()


def test_groq_client_is_created_once_and_reused():
    with patch.dict(os.environ, {}, clear=True), patch("llm.client.Groq") as groq_cls:
        create = groq_cls.return_value.chat.completions.create
        choice = MagicMock(finish_reason="stop")
        choice.message.content = "ok"
        create.return_value = MagicMock(choices=[choice], model="openai/gpt-oss-120b", usage=None)
        client._call_groq("q", "s", "reuse-key")
        client._call_groq("q", "s", "reuse-key", model="openai/gpt-oss-20b")
    groq_cls.assert_called_once_with(api_key="reuse-key", timeout=client.DEFAULT_TIMEOUT, max_retries=0)
    assert create.call_count == 2
    assert create.call_args_list[1].kwargs["model"] == "openai/gpt-oss-20b"
    assert create.call_args_list[1].kwargs["reasoning_effort"] == "low"


def test_gemini_rest_404_marks_gemini_dead(clean_providers):
    req = httpx.Request("POST", "https://example.invalid/x")
    err = httpx.HTTPStatusError("404", request=req, response=httpx.Response(404, request=req))
    with (
        patch.dict(os.environ, {"LLM_PROVIDERS": "gemini,ollama", "GEMINI_API_KEY": "k"}, clear=True),
        patch("llm.client.httpx.Client") as cls,
        patch("llm.client._call_ollama", return_value="local"),
    ):
        cls.return_value.__enter__.return_value.post.return_value.raise_for_status.side_effect = err
        assert client.generate_answer("q", "s") == "local"
    assert "gemini" in client.DEAD_PROVIDERS
