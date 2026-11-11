"""Meta-phrase cleanup, citation-free non-answers, text-about-the-text rule, chapter-13 notes,
and the narrow heaven / ahimsa boost changes."""

import logging

import pytest

from api.main import (
    load_verse_store,
    replace_supplied_phrases,
    strip_non_answer_citations,
    verify_and_clean_answer,
)
from retrieval.prompt_v2 import SYSTEM_PROMPT_V2, build_rag_prompt_v2
from retrieval.topic_boost import boost_verses


@pytest.fixture(scope="module")
def verse_store():
    return load_verse_store()


# ---------------------------------------------------------------- 1. meta leak


def test_supplied_set_sentence_from_q6():
    assert (
        replace_supplied_phrases(
            "No verse in the supplied set gives a count of the Gita's verses."
        )
        == "No verse gives a count of the Gita's verses."
    )


@pytest.mark.parametrize(
    "text, expected",
    [
        ("The verses above describe duty.", "These verses describe duty."),
        ("Among the verses above, BG 2.47 stands out.", "BG 2.47 stands out."),
        ("In this context, duty matters.", "Duty matters."),
        ("Krishna urges action in this context.", "Krishna urges action."),
        ("The given verses say this.", "These verses say this."),
        ("Krishna speaks in the supplied list of verses.", "Krishna speaks."),
    ],
)
def test_meta_phrases_rewritten(text, expected):
    assert replace_supplied_phrases(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        # 'in this context' inside normal prose: removed, sentence still reads correctly
        ("Duty, in this context, means svadharma.", "Duty means svadharma."),
        # legitimate phrases are untouched
        (
            "In the context of war, Krishna urges Arjuna to fight.",
            "In the context of war, Krishna urges Arjuna to fight.",
        ),
        ("Follow a given set of rules.", "Follow a given set of rules."),
        ("He provided food to the poor.", "He provided food to the poor."),
    ],
)
def test_in_this_context_removal_keeps_prose_readable(text, expected):
    assert replace_supplied_phrases(text) == expected


def test_full_cleanup_removes_q6_meta_leak(verse_store, caplog):
    caplog.set_level(logging.INFO)
    answer = "No verse in the supplied set gives a count of the Gita's verses."
    out, _, _, _ = verify_and_clean_answer(answer, [verse_store["2.45"]], verse_store)
    assert "supplied" not in out.lower()
    assert "META_LEAK_REMAINING" not in caplog.text


# ---------------------------------------------------------------- 2. citations on non-answers


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "The text doesn't address this directly (BG 18.63).",
            "The text doesn't address this directly.",
        ),
        (
            "No verse gives a count of verses (paraphrase, BG 2.45).",
            "No verse gives a count of verses.",
        ),
        (
            "The verses themselves don't say; traditionally, authorship is attributed to Vyasa (BG 13.1).",
            "The verses themselves don't say; traditionally, authorship is attributed to Vyasa.",
        ),
        (
            "Krishna teaches duty (BG 3.8). The text doesn't address startups directly (BG 3.9).",
            "Krishna teaches duty (BG 3.8). The text doesn't address startups directly.",
        ),
        # a contrast clause that uses a verse keeps its citation
        (
            "The text doesn't address this directly, but it teaches non-injury (BG 16.2).",
            "The text doesn't address this directly, but it teaches non-injury (BG 16.2).",
        ),
        # the next sentence is untouched
        (
            "The text doesn't address this directly (BG 18.63). Act without attachment (BG 2.47).",
            "The text doesn't address this directly. Act without attachment (BG 2.47).",
        ),
    ],
)
def test_non_answer_loses_its_citation(text, expected):
    assert strip_non_answer_citations(text) == expected


def test_q6_style_answer_has_no_citations_after_cleanup(verse_store):
    answer = (
        "### 1. What does the Bhagavad Gita say about quantum physics?\n"
        "The text doesn't address this directly (BG 18.63).\n\n"
        "### 2. Who wrote the Bhagavad Gita?\n"
        "The verses themselves don't say; traditionally, authorship is attributed to Vyasa (BG 13.1).\n\n"
        "### 3. How many verses does the Bhagavad Gita have?\n"
        "No verse in the supplied set gives a count (BG 2.45)."
    )
    ctx = [verse_store[v] for v in ("18.63", "13.1", "2.45")]
    out, _, _, _ = verify_and_clean_answer(answer, ctx, verse_store)
    assert "(BG" not in out
    assert "supplied" not in out.lower()


# ---------------------------------------------------------------- 3. prompt rules


def test_prompts_carry_new_rules_in_both_copies():
    user_v2 = build_rag_prompt_v2("q", ["q"], [])
    for text in (SYSTEM_PROMPT_V2, user_v2):
        assert (
            "Never attach a citation to a sentence saying the text doesn't address something"
            in text
        )
        assert "only cite a verse when you are using what it says" in text
        assert 'write "The verses themselves don\'t say;"' in text
        assert "701 because Arjuna's question at 13.1" in text
        assert "must be addressed, but say only what it actually says" in text
        assert "does not mean a verse answers it" in text
        assert "answer from that verse." not in text
        assert "explain the nearest verse" not in text
        assert (
            "Verse 13.8 lists qualities of knowledge (jnana); describe it that way."
            in text
        )


def test_requested_chapter13_verse_gets_note_only_when_companion_is_shown():
    v137 = {"verse_id": "13.7", "requested": True}
    v138 = {
        "verse_id": "13.8",
        "numbering_note": "Numbering note: in the 700-verse numbering, this verse is 13.7.",
    }
    prompt = build_rag_prompt_v2("q", ["q"], [v137, v138])
    assert "the user's 13.7 is probably this edition's 13.8 (shown below)" in prompt
    assert "probably this edition" not in build_rag_prompt_v2("q", ["q"], [v137])


# ---------------------------------------------------------------- 4 / A. topic boosts


@pytest.mark.parametrize(
    "text",
    [
        "How is moksha different from reaching heaven according to the Bhagavad Gita?",
        "Is svarga the final goal?",
        "Do celestial worlds last forever?",
    ],
)
def test_heaven_boost(text):
    assert boost_verses(text)[:3] == ["9.20", "9.21", "8.16"]


def test_heaven_boost_does_not_fire_on_unrelated_question():
    assert not set(boost_verses("What is karma yoga?")) & {"9.20", "9.21", "8.16"}


def test_ahimsa_no_longer_boosts_war_verses():
    boosted = boost_verses("What does the Gita say about ahimsa?")
    assert {"13.8", "16.2", "17.14"} <= set(boosted)
    assert not set(boosted) & {"2.31", "2.33", "11.33", "18.17"}
    # war questions still get the war verses
    assert "11.33" in boost_verses("Is war justified in the Gita?")


WAR_VERSES = {"2.31", "2.33", "11.33", "18.17"}


@pytest.mark.parametrize(
    "text",
    [
        "What does the Gita say about non-violence?",
        "What does the Gita say about non violence?",
        "What does the Gita say about nonviolence?",
        "What does the Gita say about non‑violence?",
    ],
)
def test_non_violence_does_not_boost_war_verses(text):
    assert not set(boost_verses(text)) & WAR_VERSES


@pytest.mark.parametrize(
    "text", ["Does the Bhagavad Gita justify violence?", "Is a violent act ever right?"]
)
def test_violence_boosts_both_sides(text):
    boosted = boost_verses(text)
    assert WAR_VERSES <= set(boosted)
    assert "16.2" in boosted
    # only the one non-injury verse is added for balance
    assert not set(boosted) & {"10.5", "13.8", "17.14"}
