import re

STOPWORDS = {
    "how", "can", "one", "does", "what", "which", "who", "whom", "whose", "why",
    "when", "where", "according", "gita", "bhagavad", "the", "and", "for", "with",
    "about", "are", "you", "your", "someone", "person", "into", "from", "that", "this"
}

def token_match(a, b):
    if a == b:
        return True
    if len(a) >= 4 and len(b) >= 4 and a[:3] == b[:3]:
        return True
    return False

def match_clause(sq: str, clauses: list[str]) -> str | None:
    sq_tokens = set(t for t in re.findall(r'[a-zA-Z]{3,}', sq.lower()) if t not in STOPWORDS)
    best_c = None
    best_score = 0
    for c in clauses:
        c_tokens = set(t for t in re.findall(r'[a-zA-Z]{3,}', c.lower()) if t not in STOPWORDS)
        overlap = sum(1 for st in sq_tokens for ct in c_tokens if token_match(st, ct))
        if overlap > best_score:
            best_score = overlap
            best_c = c
    return best_c if best_score > 0 else None

def pair_subquestions_and_clauses(sub_questions: list[str], raw_clauses: list[str]) -> dict[int, str]:
    mapping = {}
    used_clauses = set()
    for idx, sq in enumerate(sub_questions):
        available = [c for c in raw_clauses if c not in used_clauses]
        mc = match_clause(sq, available)
        if mc:
            mapping[idx] = mc
            used_clauses.add(mc)
    return mapping

sub_qs = [
    "What guidance does the Bhagavad Gita give for maintaining composure and cultivating virtue?",
    "What does the Bhagavad Gita say about practicing celibacy?",
    "According to the Bhagavad Gita, does killing a mosquito constitute a sin?",
    "According to the Bhagavad Gita, does killing a mosquito lead to hell?"
]
raw_clauses = [
    "how can i keep my composure and be virtuous",
    "follow celebacy",
    "if i kill a mosquito am i sinner",
    "am i going to hell"
]

pairs = pair_subquestions_and_clauses(sub_qs, raw_clauses)
for idx, c in pairs.items():
    print(f"SQ [{idx}] -> Clause: '{c}'")

