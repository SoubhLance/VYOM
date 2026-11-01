"""Topic-specific verse boosting for contested or sensitive philosophical inquiries.

Enforces retrieval of canonical and balanced scriptural sources for topics such as:
- food_meat: vegetarianism, offerings, diet, moderation, ahimsa
- caste: varna, duties, nature, spiritual equality
- war: righteous duty, detachment in battle, instrument of the Divine
"""

import re

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
    ],
    "hell": [
        "16.21",
        "16.16",
        "1.44",
        "1.42",
    ],
    "failure": [
        "2.47",
        "2.48",
        "2.38",
        "4.22",
    ],
}

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
        "ahimsa",
        "is war",
        "war justified",
        "justify war",
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
    ],
    "hell": [
        "hell",
        "naraka",
    ],
    "failure": [
        "failure",
        "failed",
        "fail",
        "fruit of action",
        "fruits of action",
        "results of action",
    ],
}


def boost_verses(query_or_subquestion: str) -> list[str]:
    """Return list of boosted verse_ids for a query or sub-question based on whole-word keyword matching."""
    text = query_or_subquestion.strip()
    if not text:
        return []

    matched_topics: list[str] = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            # Whole-word, case-insensitive match
            pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
            if re.search(pattern, text, re.IGNORECASE):
                if topic not in matched_topics:
                    matched_topics.append(topic)
                break

    boosted: list[str] = []
    seen: set[str] = set()
    for topic in matched_topics:
        for vid in TOPIC_VERSES.get(topic, []):
            if vid not in seen:
                seen.add(vid)
                boosted.append(vid)

    return boosted
