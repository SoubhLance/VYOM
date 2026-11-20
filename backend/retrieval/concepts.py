"""Hand-curated concept router: core Sanskrit terms -> the verses that define them.

Approved by the owner on 2026-11-19. Verses were checked against the translations in verses.jsonl
(701-verse numbering). Lists are ordered by importance: with 2+ sub-questions only the first few are used.

Matching works on a normalized form of the query, so spelling variants meet:
  diacritics stripped (ś->s, ñ->n, ā->a), lowercase, sh->s, w->v, gy/gn->jn, aa->a, ee->i, oo->u.
  e.g. 'Sthithaprajna', 'sthita-prajñasya', 'stithpragya' -> 'st(h)it(h)a prajn...'
Devanagari terms are matched on the raw text and must not be preceded by another Devanagari letter,
so परमात्मा does not count as आत्मा.

These boosts are not part of the retrieval benchmark (docs/BENCHMARK.md keeps them separate).
"""

import re
import unicodedata

_DEV = r"ऀ-ॿ"


def _dev(term: str) -> str:
    """Devanagari term not glued to a preceding Devanagari letter (inflected endings allowed)."""
    return rf"(?<![{_DEV}]){term}"


CONCEPTS: dict[str, dict[str, list[str]]] = {
    "sthitaprajna": {
        "latin": [r"\bst(h)?it(h)?a?[\s-]?prajn\w*"],
        "english": [r"\bsteady wisdom\b"],
        "devanagari": [_dev("स्थितप्रज्ञ")],
        "verses": ["2.55", "2.56", "2.54", "2.57", "2.58", "2.68"],
    },
    "sharanagati": {
        "latin": [r"\bsara?na?gati\b", r"\bsaranam\b"],
        "english": [],
        "devanagari": [_dev("शरणागति"), _dev("शरण")],
        # same order as topic_boost's "surrender" list
        "verses": ["18.66", "18.62", "18.65", "9.27", "9.34", "7.14"],
    },
    "svadharma": {
        "latin": [r"\bsva[\s-]?dharm\w*"],
        "english": [],
        "devanagari": [_dev("स्वधर्म")],
        "verses": ["3.35", "18.47", "18.48", "2.31", "2.33"],
    },
    "nishkama_karma": {
        "latin": [r"\bniskam\w*"],
        "english": [],
        "devanagari": [_dev("निष्काम")],
        "verses": ["2.47", "2.48", "3.19", "4.20", "18.9"],
    },
    "gunas": {
        "latin": [
            r"\bgunas?\b",
            r"\btri[\s-]?guna\w*",
            r"\bsatt?v(a|ic|ik)\b",
            r"\brajas(ic|ik)?\b",
            r"\btamas(ic|ik)?\b",
        ],
        "english": [],
        "devanagari": [_dev("गुण"), _dev("सत्त्व"), _dev("रजस्"), _dev("तमस्")],
        "verses": ["14.5", "14.6", "14.7", "14.8", "14.9"],
    },
    "karma_yoga": {
        "latin": [r"\bkarma?[\s-]?yog\w*"],
        "english": [],
        "devanagari": [_dev(r"कर्म\s?योग")],
        "verses": ["3.3", "3.7", "3.8", "5.2", "2.50"],
    },
    "bhakti": {
        "latin": [r"\bbhakt(i|a|as)?\b"],
        "english": [],
        "devanagari": [_dev("भक्ति")],
        "verses": ["12.2", "12.6", "12.7", "9.22", "9.34", "18.65"],
    },
    "jnana_yoga": {
        "latin": [r"\bjnan\w*"],
        "english": [],
        "devanagari": [_dev("ज्ञान")],
        "verses": ["4.33", "4.34", "4.37", "4.38", "4.39"],
    },
    "atman": {
        # \b keeps 'mahatma' and 'paramatma' out (the letter before 'atm' is a word character)
        "latin": [r"\batm(a|an)\b"],
        "english": [],
        "devanagari": [_dev("आत्मा"), _dev("आत्मन्")],
        "verses": ["2.12", "2.13", "2.20", "2.22", "2.23", "2.24"],
    },
    "paramatma": {
        "latin": [r"\bparamatm\w*"],
        "english": [],
        "devanagari": [_dev("परमात्म")],
        "verses": ["13.23", "15.17", "13.28", "6.7"],
    },
    "dhyana": {
        "latin": [r"\bdhyan\w*"],
        "english": [],
        "devanagari": [_dev("ध्यान")],
        "verses": ["6.10", "6.11", "6.12", "6.13", "6.14"],
    },
    "yajna": {
        "latin": [r"\byajn\w*"],
        "english": [],
        "devanagari": [_dev("यज्ञ")],
        "verses": ["3.9", "3.10", "3.14", "4.24", "4.25"],
    },
    "maya": {
        "latin": [r"\bmaya\b", r"\byoga[\s-]?maya\b"],
        "english": [],
        "devanagari": [_dev("माया")],
        "verses": ["7.14", "7.25", "4.6", "18.61", "7.15"],
    },
    "om_tat_sat": {
        "latin": [r"\bom[\s,]+tat[\s,]+sat\b"],
        "english": [],
        "devanagari": [r"ॐ\s*तत्\s*सत्"],
        "verses": ["17.23", "17.24", "17.25", "17.26", "17.27"],
    },
    "samatva": {
        "latin": [r"\bsamatv\w*", r"\bsamata\b"],
        "english": [],
        "devanagari": [_dev("समत्व")],
        "verses": ["2.48", "2.38", "6.9", "5.18"],
    },
    "moksha": {
        "latin": [r"\bmoks\w*", r"\bmukti\b"],
        "english": [],
        "devanagari": [_dev("मोक्ष"), _dev("मुक्ति")],
        "verses": ["18.66", "2.51", "5.26", "4.9"],
    },
}

_COMPILED = {
    name: (
        [re.compile(p) for p in c["latin"]],
        [re.compile(p) for p in c["english"]],
        [re.compile(p) for p in c["devanagari"]],
    )
    for name, c in CONCEPTS.items()
}


def normalize_concept_text(text: str) -> str:
    """Fold Latin spelling variants of Sanskrit terms onto one form (see module docstring)."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    for a, b in (
        ("sh", "s"),
        ("w", "v"),
        ("gy", "jn"),
        ("gn", "jn"),
        ("aa", "a"),
        ("ee", "i"),
        ("oo", "u"),
    ):
        t = t.replace(a, b)
    return t


def match_concepts(text: str) -> list[str]:
    """Names of the concepts the text mentions, in CONCEPTS order."""
    if not text or not text.strip():
        return []
    norm = normalize_concept_text(text)
    lower = text.lower()
    found = []
    for name, (latin, english, deva) in _COMPILED.items():
        if (
            any(p.search(norm) for p in latin)
            or any(p.search(lower) for p in english)
            or any(p.search(text) for p in deva)
        ):
            found.append(name)
    return found


def concept_verses(text: str, cap: int | None = None) -> list[str]:
    """Verses for every concept in the text, each list cut to `cap` (None = whole list), deduplicated."""
    out: list[str] = []
    for name in match_concepts(text):
        verses = CONCEPTS[name]["verses"]
        for vid in verses if cap is None else verses[:cap]:
            if vid not in out:
                out.append(vid)
    return out
