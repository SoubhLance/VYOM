import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
sys.path.insert(0, "backend/indexing")
sys.path.insert(0, "backend/retrieval")
from search import Searcher

s = Searcher("bge-m3")
for q in ["if i kill a mosquito", "if i kill a mosquito am i sinner", "am i sinner", "am i going to hell"]:
    hits = s.search(q, k=3)
    print(q, "->", [(h["verse_id"], round(h["score"], 3)) for h in hits])
s.close()

