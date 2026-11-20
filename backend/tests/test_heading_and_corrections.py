"""2026-11-19: single-question heading strip (all providers) and the Sanskrit corrections table."""

import copy
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app, strip_single_section_heading
from clean import SANSKRIT_CORRECTIONS, apply_sanskrit_corrections
from llm import client

# ---------------------------------------------------------------- heading strip

ONE = "### 1. How does Krishna advise mastering the mind?\n\nThrough practice and dispassion (BG 6.35)."


def test_strips_lone_leading_heading_for_one_sub_question():
    assert (
        strip_single_section_heading(ONE, 1)
        == "Through practice and dispassion (BG 6.35)."
    )


@pytest.mark.parametrize("heading", ["## 1) Mind", "#1. Mind", "   ### 1. Mind"])
def test_heading_variants(heading):
    assert (
        strip_single_section_heading(f"{heading}\nBody (BG 6.35).", 1)
        == "Body (BG 6.35)."
    )


def test_keeps_headings_for_several_sub_questions():
    two = "### 1. Anger\n\nA (BG 2.63).\n\n### 2. Food\n\nB (BG 17.8)."
    assert strip_single_section_heading(two, 2) == two
    assert (
        strip_single_section_heading(two, 1) == two
    )  # two headings: leave the model's structure alone


def test_keeps_heading_not_at_start_and_plain_answers():
    mid = "Intro sentence.\n### 1. Mind\nBody."
    assert strip_single_section_heading(mid, 1) == mid
    assert (
        strip_single_section_heading("Plain answer (BG 6.35).", 1)
        == "Plain answer (BG 6.35)."
    )
    assert strip_single_section_heading(ONE, None) == ONE


@pytest.mark.parametrize("provider", ["groq", "groq2", "gemini", "ollama"])
@pytest.mark.parametrize(
    "query,multi",
    [("Explain BG 6.35", True), ("How to master an agitated mind?", True)],
)
def test_api_strips_heading_for_any_provider(provider, query, multi):
    searcher = MagicMock()
    searcher.search.return_value = [
        {"verse_id": "6.35", "score": 0.9, "chunks": [("6.35:v", 0.9)]}
    ]
    app.state.searcher = searcher
    app.state.valid_ids = {"6.34", "6.35", "6.36", "6.37"}
    app.state.verse_store = {
        "6.35": {
            "verse_id": "6.35",
            "translations": {
                "english": [{"author": "A", "text": "The mind is restless."}]
            },
        }
    }
    fake = client.GenerationResult(ONE)
    fake.model = "m"
    with (
        patch("api.main.generate_answer", return_value=fake),
        patch("api.main.get_last_provider", return_value=provider),
        patch("api.main.get_last_fallback_used", return_value=provider != "groq"),
    ):
        body = (
            TestClient(app)
            .post("/api/ask", json={"query": query, "multi": multi})
            .json()
        )
    assert not body["answer"].lstrip().startswith("#")
    assert "practice and dispassion" in body["answer"]


# ---------------------------------------------------------------- Sanskrit corrections


def _verses_with_typos():
    """One record per verse holding every `old` string for it (1.26 has two corrections)."""
    by_vid: dict[str, list[str]] = {}
    for vid, old, _ in SANSKRIT_CORRECTIONS:
        by_vid.setdefault(vid, []).append(old)
    return [{"verse_id": vid, "sanskrit": " | ".join(olds)} for vid, olds in by_vid.items()]


def test_corrections_apply_each_fix_once():
    out = {v["verse_id"]: v["sanskrit"] for v in apply_sanskrit_corrections(_verses_with_typos())}
    for vid, old, new in SANSKRIT_CORRECTIONS:
        assert new in out[vid] and old not in out[vid]
    assert len(out) == 6 and sum(vid == "1.26" for vid, _, _ in SANSKRIT_CORRECTIONS) == 2


def test_corrections_fail_loudly_when_old_text_missing():
    verses = _verses_with_typos()
    verses[0]["sanskrit"] = "already fixed upstream"
    with pytest.raises(ValueError, match="expected 1 occurrence"):
        apply_sanskrit_corrections(verses)


def test_corrections_fail_loudly_on_ambiguous_or_unknown_verse():
    verses = _verses_with_typos()
    vid, old, _ = SANSKRIT_CORRECTIONS[-1]
    verses[-1]["sanskrit"] = f"{old} {old}"  # 10.29 is last, with one correction
    with pytest.raises(ValueError, match="found 2"):
        apply_sanskrit_corrections(copy.deepcopy(verses))
    with pytest.raises(ValueError, match="unknown verse"):
        apply_sanskrit_corrections(
            [v for v in _verses_with_typos() if v["verse_id"] != "4.29"]
        )
