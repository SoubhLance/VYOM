import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.path.insert(0, "backend/indexing")
sys.path.insert(0, "backend/retrieval")

from search import Searcher

s = Searcher("bge-m3")

test_qs = [
    "how to keep composure and be virtuous",
    "how to follow celibacy",
    "if I kill a mosquito am I a sinner, will I go to hell",
    "ahimsa non-violence toward living beings",
    "what leads a person to hell",
    "follow celebacy",
    "How can one practice celibacy according to the Gita?",
    "Does killing an insect or small creature incur sin?",
    "Does killing a mosquito constitute a sin?",
    "if i kill a mosquito am i sinner",
    "am i going to hell"
]

for q in test_qs:
    hits = s.search(q, k=5)
    vids = [(h["verse_id"], round(h["score"], 3)) for h in hits]
    has_target = any(vid in ["18.17", "17.14"] for vid, _ in vids)
    flag = " <--- TARGET FOUND!" if has_target else ""
    print(f"{q:<55} -> {vids}{flag}")

s.close()

