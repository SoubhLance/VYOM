"""Life-theme topic boosts (owner-approved map, 2026-11-19) and the English translation corrections."""

import copy
import json
import sys
from pathlib import Path

import pytest

from retrieval.topic_boost import LIFE_THEMES, TOPIC_VERSES, boost_verses

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ingestion"))
from clean import ENGLISH_CORRECTIONS, apply_english_corrections  # noqa: E402

VERSES_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "verses.jsonl"

APPROVED = {
    "results": ["2.47", "2.48", "2.38", "2.14", "18.66"],
    "fear": ["2.56", "2.40", "12.15", "16.1", "6.5"],
    "guilt": ["4.36", "9.30", "9.31", "18.66", "6.5"],
    "desire": ["3.37", "3.39", "3.43", "2.62", "5.23"],
    "celibacy": ["6.14", "8.11", "17.14", "2.59", "2.60"],
    "grief": ["2.11", "2.27", "2.20", "2.13", "18.66"],
    "anger": ["2.62", "2.63", "5.23", "5.26", "16.21"],
    "confusion": ["4.42", "18.63", "4.16", "2.7", "18.73"],
    "duty": ["3.35", "18.47", "3.19", "3.8"],
}


def test_map_matches_the_approved_lists():
    for theme, verses in APPROVED.items():
        assert TOPIC_VERSES[theme] == verses, theme
    assert "failure" not in TOPIC_VERSES  # replaced by "results"
    assert set(APPROVED) == LIFE_THEMES


@pytest.mark.parametrize(
    "text, theme",
    [
        ("I am waiting for my exam result", "results"),
        ("what if I fail", "results"),
        ("I feel tense and afraid", "fear"),
        ("I feel guilty about it", "guilt"),
        ("how to control lust", "desire"),
        ("how do I handle strong cravings", "desire"),
        ("how should one keep celibacy", "celibacy"),
        ("I lost my father and the grief is heavy", "grief"),
        ("I get angry easily", "anger"),
        ("I don't know what to do", "confusion"),
        ("what is my duty", "duty"),
    ],
)
def test_triggers(text, theme):
    # a single theme fits under the 6-verse cap whole
    assert boost_verses(text) == APPROVED[theme]


@pytest.mark.parametrize("text", ["What is karma yoga?", "Explain BG 2.47", "fearlessness in chapter 16"])
def test_whole_word_only(text):
    # 'fearlessness' must not trigger the fear theme
    assert not set(boost_verses(text)) & set(APPROVED["fear"]) - {"2.47"}


def test_cap_applies_to_life_themes_with_two_or_more_sub_questions():
    text = "I am afraid and anxious"
    assert boost_verses(text) == APPROVED["fear"]
    assert boost_verses(text, concept_cap=3) == APPROVED["fear"][:3]


def test_contested_topics_are_still_never_cut():
    boosted = boost_verses("Is the caste system in the Gita?", concept_cap=3)
    assert boosted[: len(TOPIC_VERSES["caste"])] == TOPIC_VERSES["caste"]


def test_two_themes_share_six_slots_round_robin():
    # results fires before fear; each keeps its first verses before either keeps a fourth
    boosted = boost_verses("I am waiting for the result and I feel afraid")
    assert boosted == ["2.47", "2.56", "2.48", "2.40", "2.38", "12.15"]


def test_cap_counts_concepts_too_and_keeps_every_first_verse():
    from retrieval.topic_boost import MAX_THEME_BOOSTS

    boosted = boost_verses("I feel anger and guilt and fear about my duty and the result")
    assert len(boosted) == MAX_THEME_BOOSTS
    for theme in ("anger", "guilt", "fear", "duty", "results"):
        assert APPROVED[theme][0] in boosted, theme


def test_multi_part_question_keeps_each_boosted_parts_first_verse():
    """A lower-scoring part (celibacy) lost every boosted verse to the fill slots of higher-scoring
    parts (desire, guilt). Its first boosted verse is now a guaranteed pick."""
    from unittest.mock import MagicMock

    from retrieval.multi import retrieve_multi

    def search(text, k=5):
        if "celibacy" in text:
            return [{"verse_id": "12.9", "score": 0.50}, {"verse_id": "16.16", "score": 0.49}]
        base = 0.80 if "cravings" in text else 0.78
        return [{"verse_id": f"18.{n}", "score": base - n / 1000} for n in range(1, 6)]

    searcher = MagicMock()
    searcher.search.side_effect = search
    subs = [
        "How should one keep celibacy during a vow?",
        "How do I handle strong cravings?",
        "How do I deal with guilt after a lapse?",
    ]
    res = retrieve_multi(searcher, " ".join(subs), per_q=5, cap=12, sub_questions=subs)
    ids = [v["verse_id"] for v in res["verses"]]
    assert "6.14" in ids  # celibacy's first boosted verse survives
    assert "3.37" in ids and "4.36" in ids  # desire and guilt keep theirs
    assert len(ids) <= 12
    themed = {v["verse_id"]: v["theme_for"] for v in res["verses"] if v.get("theme_for")}
    assert themed["6.14"] == {0: 0} and themed["4.36"] == {2: 0}


def test_prompt_lists_theme_verses_first_and_marks_them():
    from retrieval.prompt_v2 import build_rag_prompt_v2

    def rec(vid, theme_for=None):
        r = {"verse_id": vid, "for_question": [1], "translations": {"english": [{"author": "T", "text": f"text {vid}"}]}}
        if theme_for:
            r["theme_for"] = theme_for
        return r

    verses = [rec("18.6"), rec("18.9"), rec("9.30", {1: 1}), rec("4.36", {1: 0}), rec("6.14", {0: 0})]
    prompt = build_rag_prompt_v2("q", ["a", "b"], verses)
    order = [p.split(" ===")[0] for p in prompt.split("=== Bhagavad Gita Verse ")[1:]]
    assert order == ["6.14", "4.36", "9.30", "18.6", "18.9"]
    assert "Theme verse for Sub-Question 2: speaks directly to its theme" in prompt
    block_18_6 = prompt.split("=== Bhagavad Gita Verse 18.6 ===")[1].split("===")[0]
    assert "Theme verse" not in block_18_6  # semantic matches stay unmarked


# ---------------------------------------------------------------- English corrections


def _record(vid: str) -> dict:
    with open(VERSES_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r["verse_id"] == vid:
                    return r
    raise KeyError(vid)


def _raw_10_35() -> dict:
    """10.35 as the raw dataset has it: verses.jsonl is regenerated with the fix since 2026-11-20,
    so the typo is put back to test the correction itself."""
    rec = copy.deepcopy(_record("10.35"))
    for t in rec["translations"]["english"]:
        if t["author"] == "Shri Purohit Swami":
            t["text"] = t["text"].replace("of meters, I am Gayatri", "of meters, I am Garatri")
    return rec


def test_served_data_has_the_fix():
    texts = {t["author"]: t["text"] for t in _record("10.35")["translations"]["english"]}
    assert "of meters, I am Gayatri" in texts["Shri Purohit Swami"]


def test_garatri_is_corrected_to_gayatri_in_one_translation_only():
    rec = _raw_10_35()
    assert "Garatri" in json.dumps(rec)
    out = apply_english_corrections([copy.deepcopy(rec)])[0]
    texts = {t["author"]: t["text"] for t in out["translations"]["english"]}
    assert "I am Gayatri" in texts["Shri Purohit Swami"] and "Garatri" not in texts["Shri Purohit Swami"]
    others = {t["author"]: t["text"] for t in rec["translations"]["english"] if t["author"] != "Shri Purohit Swami"}
    assert all(texts[a] == t for a, t in others.items())


def test_english_correction_fails_loudly_if_text_changed():
    rec = copy.deepcopy(_record("10.35"))
    for t in rec["translations"]["english"]:
        t["text"] = t["text"].replace("Garatri", "Gayatri")
    with pytest.raises(ValueError, match="expected 1 occurrence"):
        apply_english_corrections([rec])


def test_english_corrections_table_shape():
    assert all(len(row) == 4 for row in ENGLISH_CORRECTIONS)
