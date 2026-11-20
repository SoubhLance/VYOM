import json
import re

def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def check_quotes(answer_text: str, verses: list[dict]) -> dict[str, list[str]]:
    # Extract quotes inside straight or curly quotes
    # Match strings inside "..." or “...”
    raw_quotes = re.findall(r'["“]([^"”]+)["”]', answer_text)
    
    # Filter for 6 or more words
    candidate_quotes = []
    for q in raw_quotes:
        cleaned = q.strip()
        words = cleaned.split()
        if len(words) >= 6:
            candidate_quotes.append(cleaned)
            
    # Collect candidate translations exactly as build_rag_prompt reads them
    candidate_translations = []
    for v in verses:
        trans = v.get("translations")
        if isinstance(trans, dict):
            for item in trans.get("english", []):
                if isinstance(item, dict) and "text" in item:
                    candidate_translations.append(item["text"])
                elif isinstance(item, str):
                    candidate_translations.append(item)
        elif isinstance(trans, list):
            for item in trans:
                if isinstance(item, dict) and "text" in item:
                    candidate_translations.append(item["text"])
                elif isinstance(item, str):
                    candidate_translations.append(item)
        if v.get("translation"):
            candidate_translations.append(v["translation"])
            
    normalized_translations = [normalize(t) for t in candidate_translations if t]
    
    verified = []
    unverified = []
    for q in candidate_quotes:
        norm_q = normalize(q)
        matched = False
        for norm_t in normalized_translations:
            if norm_q in norm_t:
                matched = True
                break
        if matched:
            verified.append(q)
        else:
            unverified.append(q)
            
    return {
        "verified": verified,
        "unverified": unverified
    }

# Quick test
mock_verse = {
    "verse_id": "16.21",
    "translations": {
        "english": [
            {"author": "Swami Sivananda", "text": "Tri-fold is the gate to this hell destructive of the self lust anger and greed"}
        ]
    }
}
sample_text = 'Krishna declares: "Tri-fold is the gate to this hell destructive of the self" in BG 16.21. But another said "this is completely fake and not in the text at all".'
res = check_quotes(sample_text, [mock_verse])
print("Verified:", res["verified"])
print("Unverified:", res["unverified"])

