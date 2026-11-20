import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.path.insert(0, "backend/indexing")
sys.path.insert(0, "backend/retrieval")

from search import Searcher
from multi import extract_raw_clauses, pair_subquestions_and_clauses

s = Searcher("bge-m3")

q = "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell"
raw_clauses = extract_raw_clauses(q)

sub_questions = [
    "How can one maintain composure and cultivate virtue according to the Bhagavad Gita?",
    "How does the Bhagavad Gita advise one to practice celibacy?",
    "According to the Bhagavad Gita, does killing a mosquito constitute a sin?",
    "What actions or conditions lead a person to hell according to the Bhagavad Gita?"
]
clause_map = pair_subquestions_and_clauses(sub_questions, raw_clauses)

merged = {}
per_sq_picks = {}

for idx, sq in enumerate(sub_questions):
    queries = [sq]
    rc = clause_map.get(idx)
    if rc and rc.lower().strip() != sq.lower().strip():
        queries.append(rc)
        
    sq_candidates = {}
    for q_text in queries:
        hits = s.search(q_text, k=3)
        for h in hits:
            vid = h["verse_id"]
            sc = float(h["score"])
            # Track in merged
            if vid not in merged:
                merged[vid] = {"verse_id": vid, "for_question": [idx], "score": round(sc, 4)}
            else:
                if idx not in merged[vid]["for_question"]:
                    merged[vid]["for_question"].append(idx)
                if sc > merged[vid]["score"]:
                    merged[vid]["score"] = round(sc, 4)
            # Track in per-query hits for guarantee
            if vid not in sq_candidates or sc > sq_candidates[vid]["score"]:
                sq_candidates[vid] = {"verse_id": vid, "score": sc, "is_rc": (q_text == rc)}

    # Pick top 2 for this sub-question:
    # If rc exists and has a distinct top hit, ensure both sq and rc are represented
    picks = []
    # top from sq
    sq_only = [c for c in sq_candidates.values() if not c["is_rc"]]
    sq_only.sort(key=lambda x: -x["score"])
    rc_only = [c for c in sq_candidates.values() if c["is_rc"]]
    rc_only.sort(key=lambda x: -x["score"])
    
    if sq_only:
        picks.append(sq_only[0]["verse_id"])
    if rc_only:
        for r in rc_only:
            if r["verse_id"] not in picks:
                picks.append(r["verse_id"])
                break
    for c in sorted(sq_candidates.values(), key=lambda x: -x["score"]):
        if len(picks) >= 2:
            break
        if c["verse_id"] not in picks:
            picks.append(c["verse_id"])
            
    per_sq_picks[idx] = picks[:2]

print("Guaranteed picks per SQ:")
for idx, p in per_sq_picks.items():
    print(f"  SQ {idx}: {p}")

guaranteed_vids = set()
for p in per_sq_picks.values():
    guaranteed_vids.update(p)

guaranteed_list = [merged[vid] for vid in guaranteed_vids]
remaining = [v for vid, v in merged.items() if vid not in guaranteed_vids]
remaining.sort(key=lambda x: -x["score"])

cap = 10
slots_left = max(0, cap - len(guaranteed_list))
final_verses = guaranteed_list + remaining[:slots_left]
final_verses.sort(key=lambda x: -x["score"])

print(f"\nFinal {len(final_verses)} Verses (cap={cap}):")
for v in final_verses:
    print(f"  Verse {v['verse_id']:<6} | for_question={v['for_question']} | score={v['score']}")

has_18_17 = any(v["verse_id"] == "18.17" for v in final_verses)
has_17_14 = any(v["verse_id"] == "17.14" for v in final_verses)
print(f"\nTarget check: 18.17 present? {has_18_17} | 17.14 present? {has_17_14}")

s.close()

