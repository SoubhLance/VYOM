"""2026-11-19: hand-curated concept router (retrieval/concepts.py) and its wiring into topic_boost / retrieve_multi."""

from unittest.mock import MagicMock

import pytest

from retrieval import multi
from retrieval.concepts import (
    CONCEPTS,
    concept_verses,
    match_concepts,
    normalize_concept_text,
)
from retrieval.topic_boost import TOPIC_VERSES, boost_verses


@pytest.mark.parametrize(
    "text,concept",
    [
        ("sthitaprajna", "sthitaprajna"),
        ("Who is a Sthithaprajna?", "sthitaprajna"),
        ("sthita-prajñasya kā bhāṣā", "sthitaprajna"),
        ("stithpragya kaun hai", "sthitaprajna"),
        ("a man of steady wisdom", "sthitaprajna"),
        ("स्थितप्रज्ञ के लक्षण", "sthitaprajna"),
        ("sharanagati", "sharanagati"),
        ("śaraṇāgati", "sharanagati"),
        ("sharnagati kya hai", "sharanagati"),
        ("swadharma", "svadharma"),
        ("sva-dharma", "svadharma"),
        ("स्वधर्म", "svadharma"),
        ("nishkaam karma", "nishkama_karma"),
        ("niṣkāma karma", "nishkama_karma"),
        ("three gunas", "gunas"),
        ("is this food sattvic or tamasic", "gunas"),
        ("satvik bhojan", "gunas"),
        ("karmayoga", "karma_yoga"),
        ("karm yog kya hai", "karma_yoga"),
        ("कर्म योग", "karma_yoga"),
        ("bhakti yoga", "bhakti"),
        ("gyan yoga", "jnana_yoga"),
        ("jñāna", "jnana_yoga"),
        ("aatma amar hai", "atman"),
        ("ātman", "atman"),
        ("आत्मा अमर है", "atman"),
        ("paramātmā", "paramatma"),
        ("परमात्मा कहाँ है", "paramatma"),
        ("dhyan kaise karein", "dhyana"),
        ("yagya", "yajna"),
        ("yagna", "yajna"),
        ("What is maya?", "maya"),
        ("Om Tat Sat", "om_tat_sat"),
        ("samatvam", "samatva"),
        ("moksh kaise mile", "moksha"),
        ("mukti", "moksha"),
    ],
)
def test_variants_trigger_their_concept(text, concept):
    assert concept in match_concepts(text)


@pytest.mark.parametrize(
    "text",
    ["Mahatma Gandhi read the Gita", "paramatma", "paramātmā", "परमात्मा", "mahatma"],
)
def test_atman_not_triggered_by_mahatma_or_paramatma(text):
    assert "atman" not in match_concepts(text)


def test_paramatma_triggers_its_own_entry():
    assert match_concepts("Where does the paramatma dwell?") == ["paramatma"]
    assert concept_verses("paramatma") == ["13.23", "15.17", "13.28", "6.7"]


@pytest.mark.parametrize(
    "text",
    [
        "How do I control my anger?",
        "What should I do when I feel anxious about exams?",
        "Is the soul ever born or does it ever die?",
        "What is karma?",
        "How should one stay balanced in pleasure and pain?",
        "Why should I do my own duty even if I do it imperfectly?",
        "What does the Gita say about meditation and devotion?",
        "I keep getting distracted, what does Krishna say?",
    ],
)
def test_plain_english_triggers_nothing(text):
    assert match_concepts(text) == []
    assert concept_verses(text) == []


def test_normalization():
    assert normalize_concept_text("Śaraṇāgati") == "saranagati"
    assert normalize_concept_text("Swadharma") == "svadharma"
    assert normalize_concept_text("pragya") == "prajna"


def test_sthitaprajna_order_and_cap():
    assert CONCEPTS["sthitaprajna"]["verses"][:3] == ["2.55", "2.56", "2.54"]
    assert concept_verses("sthitaprajna", cap=3) == ["2.55", "2.56", "2.54"]
    assert len(concept_verses("sthitaprajna")) == 6


def test_cap_applies_per_concept_and_dedupes():
    # nishkama karma and samatva share 2.48
    capped = concept_verses("nishkama karma and samatva", cap=3)
    assert capped == ["2.47", "2.48", "3.19", "2.38", "6.9"]


def test_topic_lists_are_never_capped():
    boosted = boost_verses(
        "What does the Gita say about caste and svadharma?", concept_cap=3
    )
    assert (
        boosted[: len(TOPIC_VERSES["caste"])] == TOPIC_VERSES["caste"]
    )  # all 10 contested-topic verses kept
    assert {"18.47", "18.48"} <= set(
        boosted
    )  # svadharma verses not already in the caste list


def test_retrieve_multi_caps_concepts_only_with_two_or_more_sub_questions():
    searcher = MagicMock()
    searcher.search.return_value = [{"verse_id": "6.26", "score": 0.6, "chunks": []}]

    one = multi.retrieve_multi(
        searcher, "sthitaprajna", sub_questions=["sthitaprajna"], cap=12
    )
    ids_one = {v["verse_id"] for v in one["verses"]}
    assert set(CONCEPTS["sthitaprajna"]["verses"]) <= ids_one  # single question: all 6

    two = multi.retrieve_multi(
        searcher,
        "sthitaprajna; anger",
        sub_questions=["What is sthitaprajna?", "How to control anger?"],
        cap=12,
    )
    ids_two = {v["verse_id"] for v in two["verses"]}
    assert {"2.55", "2.56", "2.54"} <= ids_two
    assert not {"2.57", "2.58", "2.68"} & ids_two  # capped to the first 3
