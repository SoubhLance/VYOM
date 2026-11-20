import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.path.insert(0, "backend/indexing")
sys.path.insert(0, "backend/retrieval")

from search import Searcher

s = Searcher("bge-m3")

sq1 = "How does the Bhagavad Gita advise one to practice celibacy?"
hits = s.search(sq1, k=5)
print(sq1, "->", [(h["verse_id"], round(h["score"], 3)) for h in hits])

sq2 = "According to the Bhagavad Gita, does killing a mosquito constitute a sin?"
hits = s.search(sq2, k=5)
print(sq2, "->", [(h["verse_id"], round(h["score"], 3)) for h in hits])

s.close()

