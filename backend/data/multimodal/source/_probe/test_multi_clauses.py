import os
import sys
import re

os.environ["HF_HUB_OFFLINE"] = "1"
sys.path.insert(0, "backend/indexing")
sys.path.insert(0, "backend/retrieval")
sys.stdout.reconfigure(encoding="utf-8")

from search import Searcher

q = "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell"
sub_questions = [
    "How can one maintain composure and cultivate virtue?",
    "How can one practice celibacy according to the Bhagavad Gita?",
    "Does killing a living creature or insect constitute a sin?",
    "What leads a person to hell according to the Gita?"
]

raw_clauses = [
    "how can i keep my composure and be virtuous",
    "follow celebacy",
    "if i kill a mosquito am i sinner",
    "am i going to hell"
]

s = Searcher("bge-m3")

merged = {}
for i, sq in enumerate(sub_questions):
    raw_clause = raw_clauses[i] if i < len(raw_clauses) else None
    queries_to_run = [sq]
    if raw_clause and raw_clause != sq:
        queries_to_run.append(raw_clause)

    for query_text in queries_to_run:
        hits = s.search(query_text, k=3)
        for h in hits:
            vid = h["verse_id"]
            score = float(h["score"])
            if vid not in merged:
                merged[vid] = {"verse_id": vid, "for_question": [i], "score": round(score, 4)}
            else:
                if i not in merged[vid]["for_question"]:
                    merged[vid]["for_question"].append(i)
                if score > merged[vid]["score"]:
                    merged[vid]["score"] = round(score, 4)

sorted_verses = sorted(merged.values(), key=lambda x: -x["score"])[:10]
print("Merged top 10 verses:")
for v in sorted_verses:
    print(f"  Verse {v['verse_id']:<6} | for_question={v['for_question']} | score={v['score']}")
s.close()

