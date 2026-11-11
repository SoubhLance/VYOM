"""Tests for single-verse routing through prompt v2, commentary-aware quote verification,
best-matching translation replacement, and the no-meta-language rule."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app, replace_supplied_phrases
from retrieval.prompt_v2 import (
    SYSTEM_PROMPT_V2,
    build_rag_prompt_v2,
    commentary_excerpt,
)
from retrieval.verify_quotes import (
    check_quotes_by_citation,
    resolve_quotes_and_citations,
)

T_248 = [
    {
        "author": "Swami Adidevananda",
        "text": "Abandoning attachment and established in Yoga, perform works, viewing success and failure with an even mind. Evenness of mind is said to be Yoga.",
    },
    {
        "author": "Dr. S. Sankaranarayan",
        "text": "O Dhananjaya! Establish yourself in the Yoga, perform actions while abandoning attachment, and remain even-minded in success and failure; for, even-mindedness is said to be the Yoga.",
    },
]
T_247 = [
    {
        "author": "Swami Sivananda",
        "text": "Thy right is to work only, but never with its fruits; let not the fruits of actions be thy motive, nor let thy attachment be to inaction.",
    }
]
C_247 = "Work for work's sake without attachment to the fruit brings purity of heart. The fruit is not in your hands."


def _verse(vid, translations, commentary=None):
    rec = {
        "verse_id": vid,
        "sanskrit": "x",
        "translations": {"english": translations},
        "commentaries": [],
    }
    if commentary:
        rec["commentaries"] = [
            {"author": "Swami Sivananda", "language": "english", "text": commentary}
        ]
    return rec


# ---------------------------------------------------------------- verifier unit tests


def test_replacement_uses_best_matching_translation():
    store = {"2.48": _verse("2.48", T_248)}
    answer = "Krishna says “being even-minded in success and failure is called Yoga” (BG 2.48)."
    out, warnings = resolve_quotes_and_citations(answer, [store["2.48"]], store)
    assert T_248[1]["text"] in out  # Sankaranarayan is the closest match
    assert T_248[0]["text"] not in out  # not simply the first translation
    assert warnings == []


def test_quote_from_shown_commentary_excerpt_is_accepted():
    rec = _verse("2.47", T_247, C_247)
    ctx = dict(rec, context_commentary=[{"author": "Swami Sivananda", "text": C_247}])
    answer = "Swami Sivananda comments: “Work for work's sake without attachment to the fruit brings purity of heart.” (BG 2.47)"
    out, warnings = resolve_quotes_and_citations(answer, [ctx], {"2.47": rec})
    assert out == answer
    assert warnings == []
    chk = check_quotes_by_citation(out, [ctx], strict_following=True)
    assert chk["unverified"] == [] and len(chk["verified"]) == 1


def test_commentary_not_shown_in_prompt_is_not_accepted():
    rec = _verse(
        "2.47", T_247, C_247
    )  # commentary exists on the record but was not shown
    answer = "Swami Sivananda comments: “Work for work's sake without attachment to the fruit brings purity of heart.” (BG 2.47)"
    out, warnings = resolve_quotes_and_citations(answer, [rec], {"2.47": rec})
    assert "purity of heart" not in out
    assert warnings == ["One unsupported statement was removed from the answer."]


def test_commentary_excerpt_is_english_and_cut_at_sentence():
    long_text = ("This is a sentence about duty. " * 30).strip()
    rec = {
        "commentaries": [
            {"author": "Sri Shankaracharya", "language": "sanskrit", "text": "संस्कृत"},
            {"author": "Swami Sivananda", "language": "english", "text": long_text},
        ]
    }
    ex = commentary_excerpt(rec)
    assert ex["author"] == "Swami Sivananda"
    assert len(ex["text"]) <= 500 and ex["text"].endswith(".")
    assert commentary_excerpt({"commentaries": []}) is None


# ---------------------------------------------------------------- routed endpoint


@pytest.fixture
def routed_state():
    saved = {
        k: getattr(app.state, k, None) for k in ("searcher", "valid_ids", "verse_store")
    }
    app.state.searcher = None
    app.state.valid_ids = {"2.47", "2.48", "2.49"}
    app.state.verse_store = {
        "2.47": _verse("2.47", T_247, C_247),
        "2.48": _verse("2.48", T_248, "Neighbour commentary that must not be shown."),
        "2.49": _verse(
            "2.49",
            [
                {
                    "author": "Swami Gambirananda",
                    "text": "Those who thirst for rewards are pitiable.",
                }
            ],
        ),
    }
    yield app.state
    for k, v in saved.items():
        setattr(app.state, k, v)


def test_routed_question_uses_v2_prompt_commentary_and_verifier(routed_state):
    captured = {}

    def fake_generate(prompt, system_prompt=""):
        captured["prompt"], captured["system"] = prompt, system_prompt
        return "Be steady: “being even-minded in success and failure is called Yoga” (BG 2.48). In the translations supplied, Krishna urges action."

    client = TestClient(app)
    with (
        patch("api.main.generate_answer", side_effect=fake_generate),
        patch("api.main.get_last_finish_reason", return_value="stop"),
    ):
        response = client.post(
            "/api/ask", json={"query": "Explain BG 2.47", "multi": True}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["routed"] is True
    assert captured["system"] == SYSTEM_PROMPT_V2
    # exactly one commentary excerpt, for the referenced verse only
    assert captured["prompt"].count("Commentary Excerpt:") == 1
    assert "Neighbour commentary" not in captured["prompt"]
    # verifier ran: fabricated quote replaced by the best-matching translation
    assert T_248[1]["text"] in data["answer"]
    assert (
        "being even-minded in success and failure is called Yoga" not in data["answer"]
    )
    # meta phrase rewritten
    assert "supplied" not in data["answer"]
    # shared verse_store was not mutated
    assert "context_commentary" not in routed_state.verse_store["2.47"]


# ---------------------------------------------------------------- no-meta-language rule


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "In the translations supplied, Krishna urges action.",
            "In these translations, Krishna urges action.",
        ),
        ("The supplied verses say this.", "These verses say this."),
        (
            "As the verses retrieved for this question show, act.",
            "As these verses show, act.",
        ),
    ],
)
def test_replace_supplied_phrases_both_word_orders(text, expected):
    assert replace_supplied_phrases(text) == expected


def test_prompts_carry_brevity_and_no_meta_rules():
    user_v2 = build_rag_prompt_v2("q", ["q"], [])
    for text in (SYSTEM_PROMPT_V2, user_v2):
        assert "about 250 words, split evenly across the sections" in text
        assert "### 1. <the sub-question>" in text
        assert "(paraphrase, BG x.y)" not in text
        assert "Never mention retrieval, search, context, sources" in text
        assert 'say "the verses retrieved for this question"' not in text
