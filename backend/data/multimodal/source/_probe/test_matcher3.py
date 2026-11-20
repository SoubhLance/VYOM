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

def extract_raw_clauses(query: str) -> list[str]:
    primary = re.split(r'[,;?]+|\b(?:also|and then)\b', query, flags=re.IGNORECASE)
    clauses = []
    for p in primary:
        p = p.strip()
        if not p:
            continue
        sub_parts = re.split(r'(?<=\w)\s+(?=(?:am|will|shall|is|are|do|does)\s+i\s+(?:going to hell|a sinner|hell|saved|condemned)\b)', p, flags=re.IGNORECASE)
        for sp in sub_parts:
            sp = sp.strip()
            if len(sp) > 3:
                clauses.append(sp)
    return clauses

def match_clause(sq: str, clauses: list[str]) -> str:
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

sub_qs = [
    "How can one maintain composure and cultivate virtue?",
    "How does one practice celibacy according to the Bhagavad Gita?",
    "Does killing an insect or mosquito make someone a sinner?",
    "What leads a person to hell according to the Bhagavad Gita?"
]
q = "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell"
clauses = extract_raw_clauses(q)
print("Extracted clauses:", clauses)

for sq in sub_qs:
    mc = match_clause(sq, clauses)
    print(f"SQ: '{sq}'\n -> Matched clause: '{mc}'\n")

