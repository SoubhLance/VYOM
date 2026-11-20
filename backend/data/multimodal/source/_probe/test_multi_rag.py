import json
import os
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

ROOT = Path("backend").resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "indexing"))
sys.path.insert(0, str(ROOT / "retrieval"))
sys.stdout.reconfigure(encoding="utf-8")

from search import Searcher
from retrieval.multi import retrieve_multi, decompose
from retrieval.prompt_v2 import SYSTEM_PROMPT_V2, build_rag_prompt_v2
from llm.client import generate_answer

QUERY = "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell"
OLD_TOP5 = ["18.52", "6.14", "6.10", "18.51", "9.30"]

print("="*70)
print(f"Original Query: {QUERY}")
print("="*70)

# 1. Initialize Searcher
searcher = Searcher("bge-m3")

# 2. Call retrieve_multi (LLM call 1 is inside retrieve_multi -> decompose)
multi_result = retrieve_multi(searcher, QUERY, per_q=3, cap=8)
sub_questions = multi_result["sub_questions"]
merged_verses = multi_result["verses"]

print(f"\nDecomposed Sub-Questions ({len(sub_questions)}):")
for i, sq in enumerate(sub_questions):
    print(f"  [{i}] {sq}")

print(f"\nMerged Verses ({len(merged_verses)}):")
for v in merged_verses:
    print(f"  Verse {v['verse_id']:<6} | for_question={v['for_question']} | score={v['score']}")

# Compare with old top-5
new_vids = [v["verse_id"] for v in merged_verses]
print("\n" + "="*70)
print("Comparison with Old Single-Query Top-5:")
print("="*70)
print(f"Old Top-5 (single query):    {OLD_TOP5}")
print(f"New Merged Verses (multi-q): {new_vids}")
print(f"Overlap:                     {list(set(OLD_TOP5).intersection(new_vids))}")
print(f"Newly Added Verses:          {[v for v in new_vids if v not in OLD_TOP5]}")

# 3. Load verse context from verses.jsonl for prompt generation
verses_path = ROOT / "data" / "processed" / "verses.jsonl"
verse_store = {}
with open(verses_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            verse_store[rec["verse_id"]] = rec

context_verses = []
for mv in merged_verses:
    vid = mv["verse_id"]
    base_rec = dict(verse_store.get(vid, {"verse_id": vid}))
    base_rec["for_question"] = mv["for_question"]
    base_rec["score"] = mv["score"]
    context_verses.append(base_rec)

# 4. Build prompt v2
prompt_v2 = build_rag_prompt_v2(QUERY, sub_questions, context_verses)

# 5. Call LLM (LLM call 2: answer generation)
print("\n" + "="*70)
print("Generating Final Answer with SYSTEM_PROMPT_V2 (LLM Call 2)...")
print("="*70)
answer = generate_answer(prompt_v2, system_prompt=SYSTEM_PROMPT_V2)

print("\n--- FINAL ANSWER ---")
print(answer)

searcher.close()

