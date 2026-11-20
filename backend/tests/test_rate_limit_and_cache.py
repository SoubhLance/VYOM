"""Phase 1 (2026-11-19): 429 handling, answer/splitter caches, lean LLM context."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from llm import client
from llm.cache import ANSWER_CACHE, SPLITTER_CACHE, normalize_question
from retrieval import multi
from retrieval.prompt_v2 import LENGTH_REMINDER, build_rag_prompt_v2


class FakeRateLimit(Exception):
    status_code = 429

    def __init__(self, retry_after: str | None):
        super().__init__("Error code: 429 rate_limit_exceeded")
        self.response = SimpleNamespace(
            headers={"retry-after": retry_after} if retry_after is not None else {}
        )


@pytest.fixture
def clean_providers():
    client.DEAD_PROVIDERS.clear()
    client.RATE_LIMITED_PROVIDERS.clear()
    yield
    client.DEAD_PROVIDERS.clear()
    client.RATE_LIMITED_PROVIDERS.clear()


ENV = {"LLM_PROVIDERS": "groq,ollama", "GROQ_API_KEY": "k"}

# ---------------------------------------------------------------- 429 handling


def test_short_retry_after_retries_groq_once(clean_providers):
    with (
        patch.dict(os.environ, ENV, clear=True),
        patch(
            "llm.client._call_groq",
            side_effect=[FakeRateLimit("2"), ("ok", "openai/gpt-oss-120b", False)],
        ) as g,
        patch("llm.client._call_ollama") as o,
        patch("llm.client.time.sleep") as sleep,
    ):
        ans = client.generate_answer("q", "s")
    assert ans == "ok" and g.call_count == 2
    sleep.assert_called_once_with(2.0)
    o.assert_not_called()
    assert "groq" not in client.RATE_LIMITED_PROVIDERS


def test_long_retry_after_fails_over_immediately(clean_providers):
    with (
        patch.dict(os.environ, ENV, clear=True),
        patch("llm.client._call_groq", side_effect=FakeRateLimit("30")) as g,
        patch("llm.client._call_ollama", return_value="local") as o,
        patch("llm.client.time.sleep") as sleep,
        patch("llm.client.time.time", return_value=1000.0),
    ):
        ans = client.generate_answer("q", "s")
    assert ans == "local" and ans.fallback_used is True
    assert g.call_count == 1 and o.call_count == 1
    sleep.assert_not_called()
    assert client.RATE_LIMITED_PROVIDERS["groq"] == 1030.0
    assert client.get_last_provider() == "ollama"


def test_missing_retry_after_uses_default_cooldown(clean_providers):
    with (
        patch.dict(os.environ, ENV, clear=True),
        patch("llm.client._call_groq", side_effect=FakeRateLimit(None)),
        patch("llm.client._call_ollama", return_value="local"),
        patch("llm.client.time.sleep") as sleep,
        patch("llm.client.time.time", return_value=1000.0),
    ):
        client.generate_answer("q", "s")
    sleep.assert_not_called()
    assert (
        client.RATE_LIMITED_PROVIDERS["groq"]
        == 1000.0 + client.RATE_LIMIT_DEFAULT_COOLDOWN
    )


def test_only_one_inline_retry(clean_providers):
    with (
        patch.dict(os.environ, ENV, clear=True),
        patch(
            "llm.client._call_groq",
            side_effect=[FakeRateLimit("1"), FakeRateLimit("1")],
        ) as g,
        patch("llm.client._call_ollama", return_value="local"),
        patch("llm.client.time.sleep") as sleep,
    ):
        assert client.generate_answer("q", "s") == "local"
    assert g.call_count == 2 and sleep.call_count == 1


def test_cooling_provider_is_skipped(clean_providers):
    client.RATE_LIMITED_PROVIDERS["groq"] = 10**12
    with (
        patch.dict(os.environ, ENV, clear=True),
        patch("llm.client._call_groq") as g,
        patch("llm.client._call_ollama", return_value="local"),
    ):
        assert client.generate_answer("q", "s") == "local"
    g.assert_not_called()


# ---------------------------------------------------------------- caches


def test_normalize_question():
    assert (
        normalize_question("  How to master  an Agitated mind?? ")
        == "how to master an agitated mind"
    )


@pytest.fixture
def api_state():
    searcher = MagicMock()
    searcher.search.return_value = [
        {"verse_id": "6.26", "score": 0.9, "chunks": [("6.26:v", 0.9)]}
    ]
    app.state.searcher = searcher
    app.state.valid_ids = {"6.26"}
    app.state.verse_store = {
        "6.26": {
            "verse_id": "6.26",
            "sanskrit": "ततो नियम्यैतदात्मन्येव वशं नयेत्",
            "transliteration": "tato niyamyaitad ātmany eva vaśhaṁ nayet",
            "translations": {
                "english": [
                    {"author": "Swami Sivananda", "text": "Restrain the restless mind."}
                ]
            },
        }
    }
    yield app.state


def _fake_answer(text="The mind is restrained step by step (BG 6.26)."):
    ans = client.GenerationResult(text)
    ans.model = "openai/gpt-oss-120b"
    return ans


def test_answer_cache_hit_skips_llm(api_state):
    c = TestClient(app)
    with (
        patch("api.main.generate_answer", return_value=_fake_answer()) as gen,
        patch("api.main.get_last_fallback_used", return_value=False),
        patch("api.main.get_last_provider", return_value="groq"),
    ):
        r1 = c.post(
            "/api/ask",
            json={"query": "How to master an agitated mind?", "multi": False},
        )
        r2 = c.post(
            "/api/ask",
            json={"query": "how to master an  agitated mind", "multi": False},
        )
    assert r1.status_code == r2.status_code == 200
    assert gen.call_count == 1
    assert r1.headers["X-VYOM-Cache"] == "MISS" and r2.headers["X-VYOM-Cache"] == "HIT"
    assert r2.headers["X-LLM-Provider"] == "groq"
    assert r2.json()["answer"] == r1.json()["answer"]
    assert r2.json()["query"] == "how to master an  agitated mind"


def test_answer_cache_key_includes_multi_flag(api_state):
    c = TestClient(app)
    with (
        patch("api.main.generate_answer", return_value=_fake_answer()) as gen,
        patch("api.main.get_last_fallback_used", return_value=False),
    ):
        c.post(
            "/api/ask",
            json={"query": "How to master an agitated mind?", "multi": False},
        )
        c.post(
            "/api/ask", json={"query": "How to master an agitated mind?", "multi": True}
        )
    assert gen.call_count == 2


def test_fallback_answers_are_not_cached(api_state):
    c = TestClient(app)
    with (
        patch("api.main.generate_answer", return_value=_fake_answer()) as gen,
        patch("api.main.get_last_fallback_used", return_value=True),
    ):
        c.post(
            "/api/ask",
            json={"query": "How to master an agitated mind?", "multi": False},
        )
        r = c.post(
            "/api/ask",
            json={"query": "How to master an agitated mind?", "multi": False},
        )
    assert gen.call_count == 2 and r.headers["X-VYOM-Cache"] == "MISS"
    assert len(ANSWER_CACHE) == 0


def test_errors_are_not_cached(api_state):
    c = TestClient(app)
    with patch("api.main.generate_answer", side_effect=RuntimeError("all failed")):
        r = c.post(
            "/api/ask",
            json={"query": "How to master an agitated mind?", "multi": False},
        )
    assert r.status_code == 503 and len(ANSWER_CACHE) == 0


def test_splitter_result_is_cached():
    query = "what does krishna say about anger and also how should a student handle exam fear and what is the self"
    with (
        patch.object(multi, "rule_based_split", return_value=None),
        patch.object(
            multi, "generate_answer", return_value='["Anger?", "Exam fear?"]'
        ) as gen,
    ):
        first = multi.decompose(query)
        second = multi.decompose(query.upper() + "?")
    assert first == second == ["Anger?", "Exam fear?"]
    assert gen.call_count == 1 and len(SPLITTER_CACHE) == 1


# ---------------------------------------------------------------- lean LLM context


def test_llm_context_has_no_sanskrit_or_iast_but_sources_do(api_state):
    v = api_state.verse_store["6.26"]
    prompt = build_rag_prompt_v2("q", ["q"], [dict(v)])
    assert "Sanskrit:" not in prompt and "Transliteration:" not in prompt
    assert v["sanskrit"] not in prompt and v["transliteration"] not in prompt
    assert "Restrain the restless mind." in prompt
    assert prompt.rstrip().endswith(
        "1. q\n\n" + LENGTH_REMINDER
    )  # question, sub-questions, then length cue
    c = TestClient(app)
    with patch("api.main.generate_answer", return_value=_fake_answer()):
        src = c.post("/api/ask", json={"query": "agitated mind", "multi": True}).json()[
            "sources"
        ][0]
    assert (
        src["sanskrit"] == v["sanskrit"]
        and src["transliteration"] == v["transliteration"]
    )
