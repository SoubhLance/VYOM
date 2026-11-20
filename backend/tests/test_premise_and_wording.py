"""False premises ('celibacy in the Karthik month') and faithful wording (prompt v2 rules 11-12).

Deterministic tests cover retrieval/premise.py and the prompt text. The live tests send real
questions to the LLM and are skipped unless VYOM_LIVE_LLM=1 (one Groq call per case).
"""

import json
import os
from pathlib import Path

import pytest

from retrieval.premise import REMOVED_WARNING, detach_premise_from_citations, premise_terms
from retrieval.prompt_v2 import SYSTEM_PROMPT_V2, build_rag_prompt_v2

VERSES_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "verses.jsonl"
REGRESSIONS = json.loads((Path(__file__).parent / "fixtures" / "paraphrase_regressions.json").read_text(encoding="utf-8"))
KARTIK_Q = "How does the Gita guide celibacy in the Karthik month?"


def _store() -> dict:
    with open(VERSES_PATH, encoding="utf-8") as f:
        return {r["verse_id"]: r for r in (json.loads(line) for line in f if line.strip())}


STORE = _store()


def _verses(*ids: str) -> list[dict]:
    return [{**STORE[i], "for_question": [0]} for i in ids]


# ---------------------------------------------------------------- premise detection


@pytest.mark.parametrize("spelling", ["Karthik", "Kartik", "Kartika", "Kārtika", "karthika"])
def test_kartik_spellings_are_a_premise_when_no_verse_mentions_them(spelling):
    assert premise_terms(f"Celibacy in the {spelling} month?", _verses("6.14", "12.9")) == {"kartik"}


def test_month_named_by_a_shown_verse_is_not_a_premise():
    # 10.35's translation says "among months, I am Margasheersha"
    assert premise_terms("Why is Margashirsha the best month?", _verses("10.35")) == set()


@pytest.mark.parametrize(
    "query",
    [
        "How do I practice a holistic life?",  # 'holi' must not match 'holistic'
        "I am addicted to my phone",  # modern situations are applied, not treated as premises
        "hi, what is karma yoga?",
        "What does the Gita say about desire?",
    ],
)
def test_ordinary_questions_have_no_premise(query):
    assert premise_terms(query, []) == set()


# ---------------------------------------------------------------- detaching premises from citations


def test_premise_sentence_with_citation_is_removed_and_honest_sentence_loses_citation():
    answer = (
        "The Gita says nothing about the Kartik month (BG 6.14). "
        "“He should remain seated with a placid mind, free from fear” (BG 6.14) Krishna counsels a steady mind. "
        "During Kartika, keep celibacy as BG 6.14 asks. Practice daily."
    )
    cleaned, warnings = detach_premise_from_citations(answer, KARTIK_Q, _verses("6.14", "12.9"))
    assert cleaned.startswith("The Gita says nothing about the Kartik month.")
    assert "During Kartika" not in cleaned
    assert "“He should remain seated with a placid mind, free from fear” (BG 6.14)" in cleaned
    assert warnings == [REMOVED_WARNING]


def test_premise_sentence_without_citation_is_kept():
    answer = "The Gita says nothing about the Kartik month. Self-restraint is praised (BG 6.14)."
    cleaned, warnings = detach_premise_from_citations(answer, KARTIK_Q, _verses("6.14"))
    assert cleaned == answer and warnings == []


def test_no_premise_means_no_change():
    answer = "During this month, practice (BG 6.14)."
    assert detach_premise_from_citations(answer, "How should I practice restraint?", _verses("6.14")) == (answer, [])


def test_verify_and_clean_answer_applies_the_premise_guard():
    from api.main import verify_and_clean_answer

    answer = "In the Kartik month, celibacy is the vow Krishna asks for (BG 6.14). Restraint steadies the mind."
    cleaned, warnings, _, _ = verify_and_clean_answer(answer, _verses("6.14"), STORE, n_sub_questions=1, query=KARTIK_Q)
    assert "Kartik" not in cleaned
    assert REMOVED_WARNING in warnings
    # without the query (older callers) nothing changes about premises
    untouched, _, _, _ = verify_and_clean_answer(answer, _verses("6.14"), STORE, n_sub_questions=1)
    assert "Kartik" in untouched


# ---------------------------------------------------------------- prompt rules


def test_prompt_has_false_premise_and_faithful_wording_rules():
    assert "11. False Premises:" in SYSTEM_PROMPT_V2
    assert '"The Gita says nothing about <that thing>."' in SYSTEM_PROMPT_V2
    assert "Never attach the user's premise to a verse" in SYSTEM_PROMPT_V2
    assert "12. Faithful Wording:" in SYSTEM_PROMPT_V2
    assert "never merge or swap them" in SYSTEM_PROMPT_V2
    assert "Never call a verse a ritual, practice, path or method unless its translation uses that word" in SYSTEM_PROMPT_V2


def test_false_premise_sentence_survives_the_gita_does_not_rewrite():
    # rewrite_gita_does_not turns "The Gita does not mention X" into a generic sentence; the
    # prescribed wording must pass through untouched so the user sees what was not mentioned
    from api.main import rewrite_gita_does_not, strip_non_answer_citations

    s = "The Gita says nothing about the Kartik month."
    assert rewrite_gita_does_not(s) == s
    assert strip_non_answer_citations(s) == s


# ---------------------------------------------------------------- live regressions (opt-in)

LIVE = pytest.mark.skipif(os.getenv("VYOM_LIVE_LLM") != "1", reason="live LLM call; set VYOM_LIVE_LLM=1")


ACCEPTED_GLOSSES = {
    # owner decision 2026-11-19
    "3.43": "'Karma Yoga' glossed as 'selfless action' — standard interpretation, accepted",
}


def _regression_params():
    for case in REGRESSIONS["cases"]:
        reason = ACCEPTED_GLOSSES.get(case["verse"])
        marks = [pytest.mark.xfail(reason=reason, strict=False)] if reason else []
        yield pytest.param(case, id=case["verse"], marks=marks)


@LIVE
@pytest.mark.parametrize("case", list(_regression_params()))
def test_live_paraphrase_regressions(case):
    from llm.client import generate_answer

    prompt = build_rag_prompt_v2(case["question"], [case["question"]], _verses(case["verse"]))
    answer = str(generate_answer(prompt, system_prompt=SYSTEM_PROMPT_V2)).lower()
    hits = [p for p in case["forbidden"] if p in answer]
    assert not hits, f"BG {case['verse']}: {case['error_seen']} -> found {hits}\n{answer}"
