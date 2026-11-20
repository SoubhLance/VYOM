"""Topic-specific verse boosting for contested or sensitive philosophical inquiries.

Enforces retrieval of canonical and balanced scriptural sources for topics such as:
- food_meat: vegetarianism, offerings, diet, moderation, ahimsa
- caste: varna, duties, nature, spiritual equality
- war: righteous duty, detachment in battle, instrument of the Divine
"""

import re

from retrieval.concepts import CONCEPTS, match_concepts

# At most this many life-theme + concept verses per sub-question (token budget: Groq 8K TPM)
MAX_THEME_BOOSTS = 6

TOPIC_VERSES = {
    "food_meat": [
        "9.26",
        "17.8",
        "17.9",
        "17.10",
        "6.16",
        "6.17",
        "16.2",
        "17.14",
        "13.8",
    ],
    "caste": [
        "4.13",
        "18.41",
        "18.42",
        "18.43",
        "18.44",
        "18.45",
        "18.46",
        "9.32",
        "5.18",
        "3.35",
    ],
    "war": [
        "2.31",
        "2.33",
        "11.33",
        "18.17",
    ],
    "surrender": [
        "18.66",
        "18.62",
        "18.65",
        "9.27",
        "9.34",
        "7.14",
    ],
    "ahimsa": [
        "10.5",
        "13.8",
        "16.2",
        "17.14",
    ],
    "celibacy": [
        "6.14",
        "8.11",
        "17.14",
        "2.59",
        "2.60",
    ],
    "hell": [
        "16.21",
        "16.16",
        "1.44",
        "1.42",
    ],
    # Life themes (owner-approved 2026-11-19; each verse's translation checked). They replace the
    # old "failure" topic (2.47, 2.48, 2.38, 4.22), whose keywords now map to "results".
    "results": ["2.47", "2.48", "2.38", "2.14", "18.66"],
    "fear": ["2.56", "2.40", "12.15", "16.1", "6.5"],
    "guilt": ["4.36", "9.30", "9.31", "18.66", "6.5"],
    "desire": ["3.37", "3.39", "3.43", "2.62", "5.23"],
    "grief": ["2.11", "2.27", "2.20", "2.13", "18.66"],
    "anger": ["2.62", "2.63", "5.23", "5.26", "16.21"],
    "confusion": ["4.42", "18.63", "4.16", "2.7", "18.73"],
    "duty": ["3.35", "18.47", "3.19", "3.8"],
    "heaven": [
        "9.20",
        "9.21",
        "8.16",
    ],
    # Violence questions also get the non-injury verse, so both sides are in context
    "violence_balance": [
        "16.2",
    ],
}

# Everyday-struggle themes: capped like concepts when a question has 2+ sub-questions (celibacy too,
# since its list grew to 5); the contested topics above them are never cut
LIFE_THEMES = {"results", "fear", "guilt", "desire", "grief", "anger", "confusion", "duty", "celibacy"}

# Topics whose keywords must not match a negated form ('non-violence', 'non violence');
# 'nonviolence' is already excluded by the whole-word match
NEGATION_EXCLUDED_TOPICS = {"war", "violence_balance"}

TOPIC_KEYWORDS = {
    "food_meat": [
        "meat",
        "non-veg",
        "non veg",
        "vegetarian",
        "flesh",
        "eat animals",
        "kill animals",
    ],
    "caste": [
        "caste",
        "varna",
        "varnashrama",
        "shudra",
        "brahmin",
        "brahmana",
        "untouchable",
        "kshatriya",
        "vaishya",
        "caste system",
    ],
    "war": [
        "is war",
        "war justified",
        "justify war",
        "violence",
        "violent",
        "justify violence",
    ],
    "surrender": [
        "surrender",
        "take refuge",
        "taking refuge",
        "sharanagati",
        "saranagati",
    ],
    "ahimsa": [
        "ahimsa",
        "non-violence",
        "nonviolence",
        "non-injury",
        "harmlessness",
    ],
    "celibacy": [
        "celibacy",
        "celibate",
        "brahmacharya",
        "brahmachari",
        # common misspellings seen in live questions ("celabacy")
        "celabacy",
        "celebacy",
        "celibasy",
    ],
    "hell": [
        "hell",
        "naraka",
    ],
    "results": [
        "result", "results", "outcome", "outcomes", "waiting", "success", "successful",
        "failure", "failed", "fail", "fruit of action", "fruits of action", "results of action",
    ],
    "fear": [
        "fear", "fears", "feared", "fearful", "fearing", "fearning", "afraid", "scared", "anxiety", "anxious",
        "nervous", "tense", "tensed", "tension", "worry", "worried", "worrying", "panic", "stress", "stressed",
    ],
    "guilt": [
        "guilt", "guilty", "sin", "sins", "sinful", "sinner", "shame", "ashamed", "regret", "regrets", "remorse",
    ],
    "desire": [
        "desire", "desires", "lust", "lustful", "urge", "urges", "urging", "craving", "cravings",
        "temptation", "tempted", "addiction", "addicted", "masturbation", "masturbate",
    ],
    "grief": [
        "grief", "grieve", "grieving", "sorrow", "loss", "mourning", "bereavement", "passed away",
    ],
    "anger": ["anger", "angry", "rage", "furious", "resentment"],
    "confusion": [
        "confused", "confusion", "doubt", "doubts", "dilemma", "what to do", "what should i do", "torn between",
    ],
    "duty": ["duty", "duties", "purpose", "svadharma", "swadharma"],
    "heaven": [
        "heaven",
        "heavens",
        "heavenly",
        "svarga",
        "swarga",
        "celestial",
    ],
    "violence_balance": [
        "violence",
        "violent",
        "justify violence",
    ],
}


def boost_verses(query_or_subquestion: str, concept_cap: int | None = None) -> list[str]:
    """Return list of boosted verse_ids for a query or sub-question based on whole-word keyword matching.

    Contested-topic lists (TOPIC_VERSES) come first and are never cut. Life themes (LIFE_THEMES) and
    the hand-curated concept router (retrieval/concepts.py) are each cut to `concept_cap` when given
    (multi.py passes 3 when a question has 2+ sub-questions), then share MAX_THEME_BOOSTS slots,
    round-robin, so each one that fires keeps at least its first verse.
    """
    text = query_or_subquestion.strip()
    if not text:
        return []

    matched_topics: list[str] = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            # Whole-word, case-insensitive match
            pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
            if topic in NEGATION_EXCLUDED_TOPICS:
                pattern = r"(?<!non[- \u2010\u2011])" + pattern
            if re.search(pattern, text, re.IGNORECASE):
                if topic not in matched_topics:
                    matched_topics.append(topic)
                break

    boosted: list[str] = []
    seen: set[str] = set()
    # Contested topics first, never cut (both sides must stay in context)
    for topic in matched_topics:
        if topic in LIFE_THEMES:
            continue
        for vid in TOPIC_VERSES.get(topic, []):
            if vid not in seen:
                seen.add(vid)
                boosted.append(vid)

    # Life themes and concepts share MAX_THEME_BOOSTS slots, taken round-robin so every theme or
    # concept that fired keeps its first verse before any keeps its second
    groups: list[list[str]] = []
    for topic in matched_topics:
        if topic in LIFE_THEMES:
            vids = TOPIC_VERSES.get(topic, [])
            groups.append(vids if concept_cap is None else vids[:concept_cap])
    for name in match_concepts(text):
        vids = CONCEPTS[name]["verses"]
        groups.append(vids if concept_cap is None else vids[:concept_cap])

    taken = 0
    for rank in range(max((len(g) for g in groups), default=0)):
        for g in groups:
            if taken >= MAX_THEME_BOOSTS:
                return boosted
            if rank < len(g) and g[rank] not in seen:
                seen.add(g[rank])
                boosted.append(g[rank])
                taken += 1

    return boosted
