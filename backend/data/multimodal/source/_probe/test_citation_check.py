import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_candidate_translations_by_verse(verses: list[dict]) -> dict[str, list[str]]:
    by_verse = {}
    for v in verses:
        vid = v.get("verse_id", "")
        candidates = []
        trans = v.get("translations")
        if isinstance(trans, dict):
            for item in trans.get("english", []):
                if isinstance(item, dict) and "text" in item:
                    candidates.append(item["text"])
                elif isinstance(item, str):
                    candidates.append(item)
        elif isinstance(trans, list):
            for item in trans:
                if isinstance(item, dict) and "text" in item:
                    candidates.append(item["text"])
                elif isinstance(item, str):
                    candidates.append(item)
        if v.get("translation"):
            candidates.append(v["translation"])
        if v.get("text"):
            candidates.append(v["text"])
        if v.get("embed_text"):
            candidates.append(v["embed_text"])
            
        by_verse[vid] = [normalize_text(t) for t in candidates if t]
    return by_verse

def check_quotes_by_citation(answer_text: str, verses: list[dict], strict_following: bool = False):
    trans_by_verse = extract_candidate_translations_by_verse(verses)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', answer_text) if p.strip()]
    
    citation_pattern = re.compile(r'\b(?:BG|Śrī Bhagavad‑gītā|Bhagavad Gita)\s*([0-9]{1,2}\.[0-9]{1,2})\b|\((?:BG\s*)?([0-9]{1,2}\.[0-9]{1,2})\)', re.IGNORECASE)
    
    seen_quotes = set()
    verified = []
    unverified = []
    uncited = []
    
    for p in paragraphs:
        matches = list(re.finditer(r'["“]([^"”]+?)["”]', p))
        for m in matches:
            quote = m.group(1).strip()
            words = quote.split()
            if len(words) < 4:
                continue
            if quote in seen_quotes:
                continue
            seen_quotes.add(quote)
            
            # Find nearest following citation in same paragraph
            after_text = p[m.end():]
            cit_match = citation_pattern.search(after_text)
            cited_vid = None
            if cit_match:
                cited_vid = cit_match.group(1) or cit_match.group(2)
            elif not strict_following:
                # Check preceding citation in same paragraph
                before_text = p[:m.start()]
                pre_matches = list(citation_pattern.finditer(before_text))
                if pre_matches:
                    last_m = pre_matches[-1]
                    cited_vid = last_m.group(1) or last_m.group(2)
                    
            if not cited_vid:
                uncited.append(quote)
                continue
                
            norm_q = normalize_text(quote)
            # Check if quote is substring of English translation of THAT cited verse
            target_trans = trans_by_verse.get(cited_vid, [])
            matched = any(norm_q in t for t in target_trans)
            
            if matched:
                verified.append({
                    "quote": quote,
                    "cited_verse": cited_vid
                })
            else:
                # Check if it was actually found in any other supplied verse
                found_in = None
                for other_vid, other_trans in trans_by_verse.items():
                    if any(norm_q in t for t in other_trans):
                        found_in = other_vid
                        break
                unverified.append({
                    "quote": quote,
                    "cited_verse": cited_vid,
                    "actual_verse": found_in
                })
                
    return {
        "verified": verified,
        "unverified": unverified,
        "uncited": uncited
    }

# Test with mock verses and saved answer
with open("backend/data/multimodal/source/_probe/test_cit_inspection.py", "r", encoding="utf-8") as f:
    text = f.read()

# Load real verses
verses_path = Path("backend/data/processed/verses.jsonl")
verses = []
with open(verses_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            verses.append(json.loads(line))

from test_cit_inspection import answer

res_fallback = check_quotes_by_citation(answer, verses, strict_following=False)
print("--- With Fallback (Preceding Citation in Paragraph) ---")
print("Verified:", len(res_fallback["verified"]))
for v in res_fallback["verified"]:
    print(f"  - [{v['cited_verse']}]: \"{v['quote'][:50]}...\"")
print("Unverified:", len(res_fallback["unverified"]))
for u in res_fallback["unverified"]:
    print(f"  - [{u['cited_verse']} vs {u['actual_verse']}]: \"{u['quote'][:50]}...\"")
print("Uncited:", len(res_fallback["uncited"]))

res_strict = check_quotes_by_citation(answer, verses, strict_following=True)
print("\n--- Strict Following Citation Only ---")
print("Verified:", len(res_strict["verified"]))
print("Unverified:", len(res_strict["unverified"]))
print("Uncited:", len(res_strict["uncited"]))
for uc in res_strict["uncited"]:
    print(f"  - \"{uc[:50]}...\"")

