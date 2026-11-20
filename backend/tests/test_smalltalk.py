"""Small-talk route: fixed reply, no retrieval, no LLM call; real questions still go to retrieval."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from retrieval import smalltalk


@pytest.mark.parametrize(
    "text, kind",
    [
        ("hi", "greeting"),
        ("Hi!", "greeting"),
        ("hello there", "greeting"),
        ("Hey VYOM 👋", "greeting"),
        ("namaste", "greeting"),
        ("नमस्ते", "greeting"),
        ("Jai Shri Krishna", "greeting"),
        ("good morning", "greeting"),
        ("thanks", "thanks"),
        ("Thank you so much!", "thanks"),
        ("dhanyavad", "thanks"),
        ("hi thanks", "greeting"),
        ("Who are you?", "about"),
        ("what can you do", "about"),
        ("What is VYOM?", "about"),
        ("ok", "filler"),
        ("test", "filler"),
        ("hmm", "filler"),
        ("?!", "filler"),
    ],
)
def test_small_talk_triggers(text, kind):
    assert smalltalk.classify(text) == kind


@pytest.mark.parametrize(
    "text",
    [
        "hi, what is karma yoga?",
        "hello, how do I deal with anger?",
        "karma",
        "fear",
        "BG 2.47",
        "2.47",
        "thanks, but what does 18.66 mean?",
        "who is Arjuna?",
        "what can I do about my anxiety",
        "How does the Gita guide celibacy in the Karthik month?",
        "",
    ],
)
def test_real_questions_are_not_small_talk(text):
    assert smalltalk.classify(text) is None


def test_reply_is_two_sentences_and_offers_suggestions():
    assert smalltalk.REPLY.endswith("Try one of these:")
    assert smalltalk.REPLY.count(". ") + smalltalk.REPLY.count(": ") >= 1
    assert smalltalk.reply_for("thanks").startswith("You're welcome. ")


def test_small_talk_endpoint_makes_no_llm_or_search_call():
    searcher = MagicMock()
    app.state.searcher = searcher
    with patch("api.main.generate_answer") as gen, patch("api.main.decompose") as dec:
        res = TestClient(app).post("/api/ask", json={"query": "hi", "multi": True})
    assert res.status_code == 200
    body = res.json()
    assert body["routed"] == "smalltalk"
    assert body["answer"] == smalltalk.REPLY
    assert body["sources"] == [] and body["cited_verses"] == []
    assert res.headers["X-VYOM-Route"] == "smalltalk"
    gen.assert_not_called()
    dec.assert_not_called()
    searcher.search.assert_not_called()


def test_question_after_greeting_still_reaches_retrieval():
    searcher = MagicMock()
    searcher.search.return_value = []
    app.state.searcher = searcher
    with patch("api.main.generate_answer", return_value="Karma Yoga is described (BG 3.3).") as gen:
        body = TestClient(app).post("/api/ask", json={"query": "hi, what is karma yoga?", "multi": True}).json()
    assert body["routed"] != "smalltalk"
    assert searcher.search.called
    gen.assert_called_once()
