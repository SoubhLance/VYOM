import json
import os
import re
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
from retrieval.multi import retrieve_multi, extract_raw_clauses
from retrieval.verify_quotes import check_quotes, check_quotes_by_citation

QUERY = "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell"

# 1. Reuse cached sub-questions from the last run (0 LLM calls)
CACHED_SUB_QUESTIONS = [
    "How can one maintain composure and cultivate virtue according to the Bhagavad Gita?",
    "How does the Bhagavad Gita advise one to practice celibacy?",
    "According to the Bhagavad Gita, does killing a mosquito constitute a sin?",
    "What actions or conditions lead a person to hell according to the Bhagavad Gita?"
]

print("=" * 70)
print("1. MULTI-RETRIEVAL WITH PER-SUBQUESTION GUARANTEE & CAP=10")
print("=" * 70)
print(f"Query: {QUERY}")

searcher = Searcher("bge-m3")

multi_result = retrieve_multi(searcher, QUERY, per_q=3, cap=10, sub_questions=CACHED_SUB_QUESTIONS)
sub_questions = multi_result["sub_questions"]
merged_verses = multi_result["verses"]

print(f"\nSub-Questions ({len(sub_questions)}):")
for i, sq in enumerate(sub_questions):
    print(f"  [{i}] {sq}")

raw_clauses = extract_raw_clauses(QUERY)
print(f"\nExtracted Raw Clauses ({len(raw_clauses)}):")
for i, rc in enumerate(raw_clauses):
    print(f"  [{i}] {rc}")

print(f"\nMerged Verses with for_question (Total: {len(merged_verses)}):")
for v in merged_verses:
    print(f"  Verse {v['verse_id']:<6} | for_question={v['for_question']} | score={v['score']}")

has_18_17 = any(v["verse_id"] == "18.17" for v in merged_verses)
has_17_14 = any(v["verse_id"] == "17.14" for v in merged_verses)
print(f"\nTarget check: 18.17 present? {has_18_17} | 17.14 present? {has_17_14}")

# 2. Load all verses from verses.jsonl for quote verification
verses_path = ROOT / "data" / "processed" / "verses.jsonl"
verses = []
with open(verses_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            verses.append(json.loads(line))

# 3. Load saved answer from previous run (task-1182 log) without any new LLM call
log_path = Path("C:/Users/Soubh/.gemini/antigravity/brain/d9bfa0b5-5a0e-4294-b117-4ae2b4beec52/.system_generated/tasks/task-1182.log")
answer_text = ""
if log_path.exists():
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        log_content = f.read()
    m = re.search(r"--- GENERATED ANSWER ---\s*\n(.*?)\n----------------------------------------------------------------------", log_content, re.DOTALL)
    if m:
        answer_text = m.group(1).strip()

if not answer_text:
    print("WARNING: Could not parse answer from log, fallback to saved string.")
    from test_cit_inspection import answer as answer_text

print("\n" + "=" * 70)
print("2. SAVED ANSWER TEXT FROM PREVIOUS RUN (0 LLM Calls)")
print("=" * 70)
print(answer_text)

# 4. Run Check 1: check_quotes (substring matching across all verses, >= 6 words)
print("\n" + "=" * 70)
print("3. CHECK 1: check_quotes(answer_text, verses) [>=6 words, global]")
print("=" * 70)
res1 = check_quotes(answer_text, verses)
print(f"Verified Quotes ({len(res1['verified'])}):")
for i, vq in enumerate(res1["verified"], 1):
    print(f"  {i}. \"{vq}\"")
print(f"\nUnverified Quotes ({len(res1['unverified'])}):")
for i, uq in enumerate(res1["unverified"], 1):
    print(f"  {i}. \"{uq}\"")

# 5. Run Check 2: check_quotes_by_citation (citation matching, >= 4 words)
print("\n" + "=" * 70)
print("4. CHECK 2: check_quotes_by_citation(answer_text, verses) [>=4 words, per-citation]")
print("=" * 70)

# Mode A: With Paragraph-level Fallback (preceding in same paragraph when no following)
res2_fallback = check_quotes_by_citation(answer_text, verses, strict_following=False)
print("--- Result A: Paragraph-level Citation Association (Nearest following, fallback to preceding in same bullet/paragraph) ---")
print(f"Verified ({len(res2_fallback['verified'])}):")
for i, vq in enumerate(res2_fallback["verified"], 1):
    print(f"  {i}. [Cited: BG {vq['cited_verse']}] \"{vq['quote']}\"")

print(f"\nUnverified ({len(res2_fallback['unverified'])}):")
for i, uq in enumerate(res2_fallback["unverified"], 1):
    print(f"  {i}. [Cited: BG {uq['cited_verse']} | Found in: {uq['actual_verse']}] \"{uq['quote']}\"")

print(f"\nUncited ({len(res2_fallback['uncited'])}):")
for i, uq in enumerate(res2_fallback["uncited"], 1):
    print(f"  {i}. \"{uq}\"")

# Mode B: Strict Following Citation Only
res2_strict = check_quotes_by_citation(answer_text, verses, strict_following=True)
print("\n--- Result B: Strict Following Citation Only (Requires citation strictly AFTER quote in paragraph) ---")
print(f"Verified: {len(res2_strict['verified'])}")
print(f"Unverified: {len(res2_strict['unverified'])}")
print(f"Uncited ({len(res2_strict['uncited'])}):")
for i, uq in enumerate(res2_strict["uncited"], 1):
    print(f"  {i}. \"{uq}\"")

print("\n" + "=" * 70)
print("TOTAL LLM CALLS MADE FOR THIS STEP: 0")
print("=" * 70)

searcher.close()

