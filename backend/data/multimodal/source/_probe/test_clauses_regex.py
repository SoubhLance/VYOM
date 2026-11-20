import re

def extract_raw_clauses(query: str) -> list[str]:
    parts = re.split(
        r'[,;?]+|\b(?:also|and also|and then)\b|(?<=[a-z0-9])\s+(?=(?:am|will|shall|do|does)\s+i\b)',
        query,
        flags=re.IGNORECASE
    )
    clauses = [p.strip() for p in parts if len(p.strip()) > 3]
    return clauses

q = "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell"
print("Clauses:")
for c in extract_raw_clauses(q):
    print(f"  - '{c}'")

