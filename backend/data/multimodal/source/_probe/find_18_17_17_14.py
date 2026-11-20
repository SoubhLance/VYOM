import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.path.insert(0, "backend/indexing")
sys.path.insert(0, "backend/retrieval")

from search import Searcher

s = Searcher("bge-m3")

queries = [
    "how can i keep my composure and be virtuous",
    "follow celebacy",
    "if i kill a mosquito am i sinner",
    "am i going to hell",
    "celibacy",
    "composure and virtuous",
    "virtuous",
    "ahimsa non-violence",
    "austerity of body celibacy non-injury",
]

for q in queries:
    hits = s.search(q, k=5)
    vids = [(h["verse_id"], round(h["score"], 3)) for h in hits]
    print(f"{q:<45} -> {vids}")

s.close()

