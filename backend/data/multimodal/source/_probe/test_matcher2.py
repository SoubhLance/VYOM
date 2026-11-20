import re

STOPWORDS = {
    "how", "can", "one", "does", "what", "which", "who", "whom", "whose", "why",
    "when", "where", "according", "gita", "bhagavad", "the", "and", "for", "with",
    "about", "are", "you", "your", "someone", "person", "into", "from", "that", "this"
}

def extract_raw_clauses(query: str) -> list[str]:
    parts = re.split(r'[,;?]+|\b(?:also|and also|and then)\b', query, flags=re.IGNORECASE)
    clauses = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        sub_parts = re.split(r'(?<=[a-z0-9])\s+(?=(?:am|will|shall|is|are|do|does)\s+i\b)', p, flags=re.IGNORECASE)
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
        overlap = 0
        for st in sq_tokens:
            for ct in c_tokens:
                if st == ct or st.startswith(ct[:4]) or ct.startswith(st[:4]):
                    overlap += 1
        if overlap > best_score:
            best_score = overlap
            best_c = c
    return best_c if best_score > 0 else None

sub_qs = [
    "How can one maintain composure and cultivate virtue?",
    "How does one practice celibacy according to the Gita?",
    "Does killing an insect or mosquito make someone a sinner?",
    "What leads a person to hell according to the Gita?"
]
q = "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell"
clauses = extract_raw_clauses(q)

for sq in sub_qs:
    mc = match_clause(sq, clauses)
    print(f"SQ: '{sq}'\n -> Matched clause: '{mc}'\n")

