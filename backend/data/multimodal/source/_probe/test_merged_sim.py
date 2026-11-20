import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.path.insert(0, "backend/indexing")
sys.path.insert(0, "backend/retrieval")

from search import Searcher
from multi import extract_raw_clauses, match_clause

s = Searcher("bge-m3")
q = "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell"
raw_clauses = extract_raw_clauses(q)
sub_questions = [
    "How to maintain composure and cultivate virtue?",
    "How to practice celibacy?",
    "Does killing an insect or mosquito incur sin?",
    "What leads a person to hell according to the Gita?"
]

merged = {}
for idx, sq in enumerate(sub_questions):
    hits = s.search(sq, k=3)
    for h in hits:
        vid = h["verse_id"]
        score = float(h["score"])
        if vid not in merged:
            merged[vid] = {"verse_id": vid, "for_question": [idx], "score": round(score, 4)}
        else:
            if idx not in merged[vid]["for_question"]:
                merged[vid]["for_question"].append(idx)
            if score > merged[vid]["score"]:
                merged[vid]["score"] = round(score, 4)

for rc in raw_clauses:
    mc_idx = None
    for idx, sq in enumerate(sub_questions):
        if match_clause(sq, [rc]):
            mc_idx = idx
            break
    if mc_idx is None:
        mc_idx = len(sub_questions) - 1
    hits = s.search(rc, k=3)
    for h in hits:
        vid = h["verse_id"]
        score = float(h["score"])
        if vid not in merged:
            merged[vid] = {"verse_id": vid, "for_question": [mc_idx], "score": round(score, 4)}
        else:
            if mc_idx not in merged[vid]["for_question"]:
                merged[vid]["for_question"].append(mc_idx)
            if score > merged[vid]["score"]:
                merged[vid]["score"] = round(score, 4)

sorted_verses = sorted(merged.values(), key=lambda x: -x["score"])[:8]
print("Top 8 Merged Verses:")
for v in sorted_verses:
    print(f"  Verse {v['verse_id']:<6} | for_question={v['for_question']} | score={v['score']}")

s.close()

