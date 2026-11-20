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
print("Clause map:", clause_map)

per_sq_verses = {}
for idx, sq in enumerate(sub_questions):
    queries = [sq]
    rc = clause_map.get(idx)
    if rc and rc.lower().strip() != sq.lower().strip():
        queries.append(rc)
    
    sq_merged = {}
    for q_text in queries:
        hits = s.search(q_text, k=3)
        for h in hits:
            vid = h["verse_id"]
            score = float(h["score"])
            if vid not in sq_merged or score > sq_merged[vid]:
                sq_merged[vid] = score
    
    sorted_sq = sorted(sq_merged.items(), key=lambda x: -x[1])
    per_sq_verses[idx] = sorted_sq
    print(f"\nSQ {idx} top verses:")
    for vid, sc in sorted_sq:
        print(f"  {vid}: {sc:.4f}")

s.close()

