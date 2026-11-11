"""Verse-reference routing: every reference retrieved, ranges, chapter-13 numbering, forced-verse caps,
single-verse path preserved, and the grounding / no-meta prompt rules."""

import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import (
    app,
    load_verse_store,
    rewrite_gita_does_not,
    verify_and_clean_answer,
)
from retrieval.multi import retrieve_multi
from retrieval.prompt_v2 import SYSTEM_PROMPT_V2, build_rag_prompt_v2
from retrieval.router import (
    MAX_FORCED_VERSES,
    build_forced_refs,
    load_valid_ids,
    parse_verse_ref,
    parse_verse_refs,
)

Q_MULTI_REF = (
    "Why does Arjuna's grief begin at 1.26, what does 4.29 say about breath control as sacrifice, "
    "and what does 9.25 say about becoming like what you worship?"
)
Q_VIOLENCE = (
    "Does the Gita justify violence, how does that square with ahimsa in 13.7 and 16.2, "
    "and what do 2.19-2.20 say about killing?"
)
NO_ADDR = "The text doesn't address this directly."


@pytest.fixture(scope="module")
def valid_ids():
    ids = load_valid_ids()
    assert len(ids) == 701
    return ids


@pytest.fixture(scope="module")
def verse_store():
    return load_verse_store()


# ---------------------------------------------------------------- router


def test_all_references_found_in_order(valid_ids):
    assert parse_verse_refs(Q_MULTI_REF, valid_ids) == ["1.26", "4.29", "9.25"]
    assert parse_verse_refs(
        "Explain BG 2.47, then tell me how to apply it to exam stress, and how it differs from 3.19.",
        valid_ids,
    ) == ["2.47", "3.19"]


@pytest.mark.parametrize(
    "text",
    ["2.19-2.20", "BG 2.19–20", "2.19 to 2.20", "what do 2.19-2.20 say about killing?"],
)
def test_range_retrieves_both_verses(text, valid_ids):
    assert parse_verse_refs(text, valid_ids) == ["2.19", "2.20"]


def test_range_expansion_capped_at_five(valid_ids):
    assert parse_verse_refs("2.10-2.30", valid_ids) == [
        "2.10",
        "2.11",
        "2.12",
        "2.13",
        "2.14",
    ]


def test_chapter_only_is_not_a_verse_reference(valid_ids):
    assert parse_verse_refs("Explain chapter 12", valid_ids) == []
    assert parse_verse_ref("Explain chapter 12", valid_ids) is None
    # 'ch' inside a word no longer splits '13' into chapter 1 verse 3
    assert parse_verse_refs("what is the approach 13.7 takes", valid_ids) == ["13.7"]


def test_forced_refs_capped_and_chapter13_companion(valid_ids):
    many = ["1.1", "2.1", "3.1", "4.1", "5.1", "6.1", "7.1", "8.1"]
    out = build_forced_refs(many, valid_ids)
    assert (
        out["refs"] == many[:MAX_FORCED_VERSES]
        and out["dropped"] == many[MAX_FORCED_VERSES:]
    )

    out = build_forced_refs(["13.7"], valid_ids)
    assert out["refs"] == ["13.7", "13.8"]
    assert out["aliases"] == {"13.8": "13.7"}
    assert "700-verse numbering, this verse is 13.7" in out["notes"]["13.8"]


# ---------------------------------------------------------------- multi retrieval


def test_retrieve_multi_assigns_each_reference_to_its_sub_question():
    searcher = MagicMock()
    searcher.search.return_value = [{"verse_id": "6.26", "score": 0.9}]
    subs = [
        "Why does Arjuna's grief begin at BG 1.26?",
        "What does BG 4.29 say about breath control as sacrifice?",
        "What does BG 9.25 say about becoming like what one worships?",
    ]
    res = retrieve_multi(
        searcher, Q_MULTI_REF, sub_questions=subs, forced_refs=["1.26", "4.29", "9.25"]
    )
    by_id = {v["verse_id"]: v for v in res["verses"]}
    assert [v["verse_id"] for v in res["verses"][:3]] == ["1.26", "4.29", "9.25"]
    assert by_id["1.26"]["for_question"] == [0]
    assert by_id["4.29"]["for_question"] == [1]
    assert by_id["9.25"]["for_question"] == [2]
    assert all(by_id[r]["forced"] for r in ("1.26", "4.29", "9.25"))


def test_retrieve_multi_falls_back_to_raw_clause_when_sub_question_drops_the_number():
    searcher = MagicMock()
    searcher.search.return_value = [{"verse_id": "6.26", "score": 0.9}]
    subs = [
        "What does the Gita teach about duty?",
        "How does the Gita link sacrifice and work?",
    ]
    res = retrieve_multi(
        searcher,
        "what does 2.47 say about duty, and how does 3.19 relate",
        sub_questions=subs,
        forced_refs=["2.47", "3.19"],
    )
    ids = [v["verse_id"] for v in res["verses"]]
    assert "2.47" in ids and "3.19" in ids


# ---------------------------------------------------------------- /api/ask


@pytest.fixture
def api_state(valid_ids, verse_store):
    saved = {
        k: getattr(app.state, k, None) for k in ("searcher", "valid_ids", "verse_store")
    }
    searcher = MagicMock()
    searcher.search.return_value = [{"verse_id": "6.26", "score": 0.9, "chunks": []}]
    app.state.searcher = searcher
    app.state.valid_ids = valid_ids
    app.state.verse_store = verse_store
    yield app.state
    for k, v in saved.items():
        setattr(app.state, k, v)


def _ask(query, subs=None, multi=True):
    captured = {}

    def fake_generate(prompt, system_prompt=""):
        captured["prompt"] = prompt
        captured["system"] = system_prompt
        return NO_ADDR

    decompose_mock = MagicMock(return_value=subs or [query])
    with (
        patch("api.main.generate_answer", side_effect=fake_generate),
        patch("api.main.decompose", decompose_mock),
    ):
        r = TestClient(app).post("/api/ask", json={"query": query, "multi": multi})
    assert r.status_code == 200, r.text
    return r.json(), captured, decompose_mock


def test_multi_reference_question_retrieves_every_referenced_verse(api_state, caplog):
    caplog.set_level(logging.INFO)
    subs = [
        "Why does Arjuna's grief begin at BG 1.26?",
        "What does BG 4.29 say about breath control as sacrifice?",
        "What does BG 9.25 say about becoming like what one worships?",
    ]
    data, captured, decompose_mock = _ask(Q_MULTI_REF, subs)
    decompose_mock.assert_called_once()
    assert data["routed"] is False
    assert data["sub_questions"] == subs
    by_id = {s["verse_id"]: s for s in data["sources"]}
    for i, vid in enumerate(["1.26", "4.29", "9.25"]):
        assert vid in data["cited_verses"]
        assert by_id[vid]["for_question"] == [i]
        assert f"=== Bhagavad Gita Verse {vid} ===" in captured["prompt"]
    # the tag line, not the rule text that mentions it
    assert captured["prompt"].count("\nRequested by the user\n") == 3
    assert "ROUTE: multi refs=['1.26', '4.29', '9.25']" in caplog.text
    assert "FORCED_REFS: sq=2 -> ['4.29']" in caplog.text


def test_range_question_retrieves_both_verses(api_state):
    data, captured, _ = _ask("What do 2.19-2.20 say about killing?")
    assert {"2.19", "2.20"} <= set(data["cited_verses"])
    assert "=== Bhagavad Gita Verse 2.19 ===" in captured["prompt"]
    assert "=== Bhagavad Gita Verse 2.20 ===" in captured["prompt"]


def test_chapter13_reference_adds_tagged_next_verse_in_multi_path(api_state):
    subs = [
        "Does the Bhagavad Gita justify violence?",
        "How does the Gita's view on violence square with ahimsa in 13.7 and 16.2?",
        "What do BG 2.19-2.20 say about killing?",
    ]
    data, captured, _ = _ask(Q_VIOLENCE, subs)
    ids = data["cited_verses"]
    assert {"13.7", "13.8", "16.2", "2.19", "2.20"} <= set(ids)
    by_id = {s["verse_id"]: s for s in data["sources"]}
    assert by_id["13.8"]["for_question"] == [1]
    assert by_id["2.20"]["for_question"] == [2]
    # the note is on both the requested verse (13.7) and its companion (13.8)
    assert REQUESTED_13_7_NOTE in _verse_block(captured["prompt"], "13.7")
    assert COMPANION_13_8_NOTE in _verse_block(captured["prompt"], "13.8")


def test_chapter13_single_verse_tags_next_verse(api_state):
    data, captured, decompose_mock = _ask("13.7")
    assert data["routed"] is True
    decompose_mock.assert_not_called()
    assert REQUESTED_13_7_NOTE in _verse_block(captured["prompt"], "13.7")
    assert COMPANION_13_8_NOTE in _verse_block(captured["prompt"], "13.8")


REQUESTED_13_7_NOTE = "Numbering note: in 700-verse numbering the user's 13.7 is probably this edition's 13.8 (shown below)."
COMPANION_13_8_NOTE = "Numbering note: in the 700-verse numbering, this verse is 13.7."


def _verse_block(prompt: str, vid: str) -> str:
    """The prompt text of one verse, from its header to the next verse header."""
    start = prompt.index(f"=== Bhagavad Gita Verse {vid} ")
    nxt = prompt.find("\n=== Bhagavad Gita Verse ", start + 1)
    return prompt[start : nxt if nxt != -1 else len(prompt)]


def test_single_verse_question_keeps_single_verse_path(api_state, caplog):
    caplog.set_level(logging.INFO)
    data, captured, decompose_mock = _ask("Explain BG 2.47")
    assert data["routed"] is True
    assert data["cited_verses"] == ["2.47"]
    assert [s["verse_id"] for s in data["sources"]] == ["2.47", "2.48", "2.49"]
    decompose_mock.assert_not_called()
    api_state.searcher.search.assert_not_called()
    assert "Commentary Excerpt:" in captured["prompt"]
    assert "ROUTE: single_verse ref=2.47" in caplog.text


@pytest.mark.parametrize("multi", [True, False])
def test_chapter_only_question_uses_semantic_path(api_state, multi):
    data, _, _ = _ask("Explain chapter 12", multi=multi)
    assert data["routed"] is False
    assert data["cited_verses"] == ["6.26"]
    api_state.searcher.search.assert_called()


def test_too_many_references_are_truncated_and_logged(api_state, caplog):
    caplog.set_level(logging.INFO)
    q = "Compare 1.1, 2.2, 3.3, 4.4, 5.5, 6.6 and 7.7, and tell me what they share?"
    data, captured, _ = _ask(q, [q])
    assert "FORCED_REFS_TRUNCATED" in caplog.text
    assert "7.7" not in data["cited_verses"]
    assert captured["prompt"].count("\nRequested by the user\n") == MAX_FORCED_VERSES


# ---------------------------------------------------------------- prompt and post-processing


def test_prompts_carry_grounding_rule():
    user_v2 = build_rag_prompt_v2("q", ["q"], [])
    for text in (SYSTEM_PROMPT_V2, user_v2):
        assert (
            "Only state what the cited verse says, and only cite a verse when you are using what it says. "
            "Never cite or quote a verse not shown above." in text
        )
        assert NO_ADDR in text
        assert "I did not find a verse" not in text
        # rule 4 shows the citation format with a placeholder, not real verses
        assert "16.21" not in text and "18.17" not in text
        assert "Never mention retrieval, search, context, sources" in text


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "The Gita does not mention mosquitoes, but it teaches non-injury (BG 16.2).",
            "The text doesn't address this directly, but it teaches non-injury (BG 16.2).",
        ),
        (
            "However, the Gita never says that startups are wrong.",
            "However, the text doesn't address this directly.",
        ),
        (
            "The Bhagavad Gita doesn't explicitly discuss physics.",
            "The text doesn't address this directly.",
        ),
        (
            "The Gita does not prohibit action “Do your duty” (BG 3.8).",
            "The text does not prohibit action “Do your duty” (BG 3.8).",
        ),
    ],
)
def test_rewrite_gita_does_not_uses_prompt_wording(text, expected):
    out = rewrite_gita_does_not(text)
    assert out == expected
    assert "retrieved" not in out.lower()


def test_cleanup_never_reintroduces_meta_phrasing(verse_store):
    ctx = [verse_store["2.47"]]
    answer = "The Gita does not mention exams. As the verses retrieved for this question show, act."
    out, _, _, _ = verify_and_clean_answer(answer, ctx, verse_store)
    for phrase in ("retrieved", "supplied", "provided"):
        assert phrase not in out.lower()
    assert out.startswith(NO_ADDR)
