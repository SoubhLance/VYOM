import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
sys.path.insert(0, "backend/indexing")
sys.path.insert(0, "backend/retrieval")
sys.stdout.reconfigure(encoding="utf-8")

from search import Searcher

s = Searcher("bge-m3")
queries = [
    "How can one maintain composure and cultivate virtue?",
    "How can one practice celibacy according to the Bhagavad Gita?",
    "Does killing a mosquito constitute a sin?",
    "What actions lead a person to hell according to Hindu philosophy?",
    "what leads a person to hell",
    "how can i keep my composure and be virtuous",
    "follow celebacy",
    "if i kill a mosquito am i sinner",
    "am i going to hell",
]
for q in queries:
    hits = s.search(q, k=3)
    hit_strs = [f"{h['verse_id']} ({h['score']:.3f})" for h in hits]
    print(f"{q:<60} -> {hit_strs}")
s.close()

