"""Test client for VYOM API verifying multi-question RAG and quote checking."""

import json
import re
import sys
from pathlib import Path
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

def load_verse_store() -> dict[str, dict]:
    vpath = REPO_ROOT / "backend" / "data" / "processed" / "verses.jsonl"
    verses = {}
    with open(vpath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                item = json.loads(line)
                verses[item["verse_id"]] = item
    return verses

from backend.retrieval.verify_quotes import check_quotes_by_citation

BASE_URL = "http://127.0.0.1:8000/api/ask"

QUERIES = [
    {
        "id": 1,
        "query": "how can i keep my composure and be virtuous, follow celebacy, also if i kill a mosquito am i sinner am i going to hell",
        "multi": True,
    },
    {
        "id": 2,
        "query": "what is dharma",
        "multi": True,
    },
    {
        "id": 3,
        "query": "I am anxious about my exams, how can the Gita help",
        "multi": True,
    },
    {
        "id": 4,
        "query": "2.47",
        "multi": True,
    },
    {
        "id": 5,
        "query": "What does Krishna say about anger and also about food",
        "multi": True,
    },
    {
        "id": 6,
        "query": "how can i keep my composure",
        "multi": False,
    },
]


def post_query(query: str, multi: bool | None = None) -> dict:
    payload = {"query": query}
    if multi is not None:
        payload["multi"] = multi
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_cited_verses_in_answer(answer: str, available_vids: set[str]) -> list[str]:
    # Match patterns like BG 2.47, (BG 16.21), 16.21, etc.
    found = []
    # Check explicit mentions of known verse_ids
    for vid in available_vids:
        pattern = r"\b" + re.escape(vid) + r"\b"
        if re.search(pattern, answer):
            found.append(vid)
    # Sort by appearance in text
    found.sort(key=lambda v: answer.find(v))
    return found


def main():
    print("Loading verse store for verification...")
    verse_store = load_verse_store()
    print(f"Loaded {len(verse_store)} verses.")

    results = []

    for item in QUERIES:
        qid = item["id"]
        qtext = item["query"]
        multi = item["multi"]
        print(f"\n{'='*70}\nRunning Test {qid}: multi={multi}\nQuery: {qtext}\n{'='*70}")

        try:
            resp = post_query(qtext, multi=multi)
        except Exception as e:
            print(f"ERROR executing query: {e}")
            results.append({"id": qid, "error": str(e)})
            continue

        answer = resp.get("answer", "")
        sources = resp.get("sources", [])
        sub_questions = resp.get("sub_questions", [])
        warnings = resp.get("warnings", [])
        cited_verses = resp.get("cited_verses", [])

        # Build mapping of vid -> for_question
        vid_to_fq = {}
        for s in sources:
            vid = s.get("verse_id")
            if vid:
                vid_to_fq[vid] = s.get("for_question", [])

        # Find which verses are cited in the answer text
        source_vids = set(vid_to_fq.keys())
        cited_in_text = extract_cited_verses_in_answer(answer, source_vids)
        if not cited_in_text:
            cited_in_text = cited_verses

        # Run quote verification
        context_verses = [verse_store[vid] for vid in source_vids if vid in verse_store]
        chk = check_quotes_by_citation(answer, context_verses, strict_following=True)

        res_record = {
            "id": qid,
            "query": qtext,
            "multi": multi,
            "routed": resp.get("routed", False),
            "sub_questions": sub_questions,
            "cited_in_text_with_fq": [(vid, vid_to_fq.get(vid, [])) for vid in cited_in_text],
            "all_cited_verses_with_fq": [(vid, vid_to_fq.get(vid, [])) for vid in cited_verses],
            "verified_count": len(chk.get("verified", [])),
            "unverified_count": len(chk.get("unverified", [])),
            "uncited_count": len(chk.get("uncited", [])),
            "warnings": warnings,
            "answer_preview": answer[:300] + ("..." if len(answer) > 300 else ""),
            "full_answer": answer,
        }
        results.append(res_record)

        print(f"Routed: {res_record['routed']}")
        print(f"Sub-questions: {sub_questions}")
        print(f"Cited verses in answer with for_question:")
        for vid, fq in res_record["cited_in_text_with_fq"]:
            print(f"  - BG {vid}: for_question={fq}")
        print(f"Quotes verification:")
        print(f"  Verified: {res_record['verified_count']}")
        print(f"  Unverified: {res_record['unverified_count']}")
        print(f"  Uncited: {res_record['uncited_count']}")
        print(f"Warnings ({len(warnings)}): {warnings}")

    with open("backend/data/multimodal/source/_probe/test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nAll tests completed and saved to test_results.json")


if __name__ == "__main__":
    main()
