"""Tests for gpt-oss reasoning settings (all Groq calls, incl. the LLM splitter),
truncation without a visible label, and removal of internal labels from answers."""

import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import llm.client as client
from api.main import app, strip_internal_labels
from retrieval import multi
from retrieval.verify_quotes import normalize_single_quotes, unquote_paraphrases


def _completion(text="ok", model="openai/gpt-oss-120b", finish="stop"):
    comp = MagicMock()
    choice = MagicMock()
    choice.message.content = text
    choice.finish_reason = finish
    comp.choices = [choice]
    comp.model = model
    comp.usage = None
    return comp


# ---------------------------------------------------------------- reasoning settings


def test_gpt_oss_gets_low_effort_and_hidden_reasoning():
    kwargs = {"model": "openai/gpt-oss-20b"}
    with patch.dict(os.environ, {}, clear=True):
        client._apply_reasoning_settings(kwargs)
    assert kwargs["reasoning_effort"] == "low"
    assert kwargs["include_reasoning"] is False


def test_env_effort_overrides_for_gpt_oss_and_other_models():
    with patch.dict(os.environ, {"GROQ_REASONING_EFFORT": "medium"}, clear=True):
        gpt = {"model": "openai/gpt-oss-120b"}
        other = {"model": "qwen/qwen3.8-27b"}
        client._apply_reasoning_settings(gpt)
        client._apply_reasoning_settings(other)
    assert gpt["reasoning_effort"] == "medium" and gpt["include_reasoning"] is False
    assert other == {"model": "qwen/qwen3.8-27b", "reasoning_effort": "medium"}


def test_non_reasoning_model_gets_no_reasoning_params():
    kwargs = {"model": "llama-3.1-8b-instant"}
    with patch.dict(os.environ, {}, clear=True):
        client._apply_reasoning_settings(kwargs)
    assert kwargs == {"model": "llama-3.1-8b-instant"}


def test_model_not_found_fallback_applies_gpt_oss_settings():
    with (
        patch.dict(os.environ, {"GROQ_MODEL": "llama-3.3-70b-versatile"}, clear=True),
        patch("llm.client.Groq") as groq_cls,
    ):
        create = groq_cls.return_value.chat.completions.create
        create.side_effect = [
            Exception("Error code: 404 model_not_found"),
            _completion("fine"),
        ]
        text, model, fallback = client._call_groq("q", "s", "k")
    assert (text, model, fallback) == ("fine", "openai/gpt-oss-120b", True)
    first, second = create.call_args_list
    assert "reasoning_effort" not in first.kwargs
    assert second.kwargs["model"] == "openai/gpt-oss-120b"
    assert second.kwargs["reasoning_effort"] == "low"
    assert second.kwargs["include_reasoning"] is False


def test_llm_splitter_call_uses_gpt_oss_settings():
    """decompose() goes through generate_answer -> _call_groq, so it gets the same settings."""
    client.DEAD_PROVIDERS.clear()
    client.RATE_LIMITED_PROVIDERS.clear()
    query = "what does krishna say about anger and also how should a student handle exam fear and what is the self"
    multi._DECOMPOSE_CACHE.pop(query, None)
    with (
        patch.dict(
            os.environ, {"GROQ_API_KEY": "k", "LLM_PROVIDERS": "groq"}, clear=True
        ),
        patch.object(multi, "rule_based_split", return_value=None),
        patch("llm.client.Groq") as groq_cls,
    ):
        create = groq_cls.return_value.chat.completions.create
        create.return_value = _completion(
            '["What does Krishna say about anger?", "How to handle exam fear?"]'
        )
        parts = multi.decompose(query)
    assert parts == ["What does Krishna say about anger?", "How to handle exam fear?"]
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-oss-120b"
    assert kwargs["reasoning_effort"] == "low"
    assert kwargs["include_reasoning"] is False
    assert kwargs["temperature"] == 0.0


# ---------------------------------------------------------------- truncation


def test_truncated_answer_has_no_visible_label():
    out = client.clean_truncated_answer(
        "First point is complete. Second point is cut mid"
    )
    assert out == "First point is complete."
    assert "shortened" not in out


def test_multi_false_path_reports_truncation_as_warning():
    saved = {
        k: getattr(app.state, k, None) for k in ("searcher", "valid_ids", "verse_store")
    }
    searcher = MagicMock()
    searcher.search.return_value = [{"verse_id": "6.26", "score": 0.9, "chunks": []}]
    app.state.searcher = searcher
    app.state.valid_ids = {"6.26"}
    app.state.verse_store = {
        "6.26": {"verse_id": "6.26", "translations": {"english": []}}
    }
    try:
        with (
            patch("api.main.generate_answer", return_value="Calm the mind."),
            patch("api.main.get_last_finish_reason", return_value="length"),
        ):
            r = TestClient(app).post(
                "/api/ask",
                json={"query": "how to calm a restless mind", "multi": False},
            )
    finally:
        for k, v in saved.items():
            setattr(app.state, k, v)
    assert r.status_code == 200
    assert r.json()["warnings"] == ["truncated"]


# ---------------------------------------------------------------- internal labels


def test_strip_internal_labels():
    assert (
        strip_internal_labels("Lift yourself (paraphrase, BG 6.5).")
        == "Lift yourself (BG 6.5)."
    )
    assert (
        strip_internal_labels("Act without craving (my inference).")
        == "Act without craving."
    )
    assert (
        strip_internal_labels("Done. My inference is that duty purifies.")
        == "Done. Duty purifies."
    )
    assert (
        strip_internal_labels("“Quote here today please” (BG 2.47)")
        == "“Quote here today please” (BG 2.47)"
    )


def test_paraphrase_never_stays_in_quotes():
    text = "Krishna urges “one must lift oneself by oneself” (paraphrase, BG 6.5)."
    out = strip_internal_labels(unquote_paraphrases(text))
    assert out == "Krishna urges one must lift oneself by oneself (BG 6.5)."


def test_single_quoted_passages_become_checkable_quotes():
    text = "He said 'let a man lift himself by himself' (BG 6.5). It's 'dharma'."
    out = normalize_single_quotes(text)
    assert "“let a man lift himself by himself”" in out
    assert "It's 'dharma'." in out  # apostrophes and short scare quotes untouched
