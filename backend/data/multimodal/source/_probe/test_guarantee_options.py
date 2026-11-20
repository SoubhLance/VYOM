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

# Let's inspect per-subquestion hits:
print("--- Per-query hits (k=3) ---")
sq_hits = {}
rc_hits = {}
for idx, sq in enumerate(sub_questions):
    h_sq = s.search(sq, k=3)
    sq_hits[idx] = h_sq
    print(f"SQ {idx} ({sq[:40]}...): {[h['verse_id'] for h in h_sq]}")
    rc = clause_map.get(idx)
    if rc:
        h_rc = s.search(rc, k=3)
        rc_hits[idx] = h_rc
        print(f"  RC {idx} ('{rc}'): {[h['verse_id'] for h in h_rc]}")

s.close()

