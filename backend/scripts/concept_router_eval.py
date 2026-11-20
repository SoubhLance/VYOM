"""Concept-router before/after on the serving retrieval path (retrieve_multi), no LLM calls.
    .\\venv\\python.exe -I backend\\scripts\\concept_router_eval.py before
    .\\venv\\python.exe -I backend\\scripts\\concept_router_eval.py after
Writes backend/_scratch/concept_router_<label>.json.

Token estimate: calibrated on a real Groq measurement. "How to master an agitated mind?" (multi path, bge-m3,
current prompt) sent 2,060 prompt tokens on 2026-11-19; about 70 of those are fixed chat-format overhead.
"""

import json
import os
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B))
os.chdir(B)
sys.stdout.reconfigure(encoding="utf-8")
os.environ["LLM_PROVIDERS"] = (
    "none"  # any accidental LLM call fails instead of spending tokens
)

from api.main import load_verse_store  # noqa: E402
from retrieval.multi import retrieve_multi, rule_based_split  # noqa: E402
from retrieval.prompt_v2 import SYSTEM_PROMPT_V2, build_rag_prompt_v2  # noqa: E402
from retrieval.search import Searcher  # noqa: E402

label = sys.argv[1] if len(sys.argv) > 1 else "run"
if (
    len(sys.argv) > 2 and sys.argv[2] == "--no-cap"
):  # measure what the per-concept cap saves
    from retrieval import multi as _multi

    _multi.MULTI_SUBQ_CONCEPT_CAP = None
MEASURED_TOKENS, OVERHEAD = 2060, 70
HARD = [
    ("sthitaprajna", {"2.54", "2.55"}),
    ("What are the marks of a sthitaprajna?", {"2.54", "2.55"}),
    ("svadharma", {"2.31", "2.33", "3.35", "18.47"}),
    ("What does the Gita say about sattva, rajas and tamas?", {"14.5"}),
    ("sharanagati", {"18.66"}),
]
MULTI_Q = "What is sthitaprajna; what is svadharma; how do I control anger"
store = load_verse_store()


def prompt_for(searcher, query, sub_questions):
    res = retrieve_multi(searcher, query, per_q=5, cap=12, sub_questions=sub_questions)
    ctx = []
    for mv in res["verses"]:
        rec = dict(store[mv["verse_id"]])
        rec["for_question"] = mv.get("for_question", [])
        ctx.append(rec)
    return (
        [mv["verse_id"] for mv in res["verses"]],
        SYSTEM_PROMPT_V2,
        build_rag_prompt_v2(query, sub_questions, ctx),
    )


out = {"label": label}
# calibration on bge-m3 (the measured request used bge-m3)
s = Searcher("bge-m3")
try:
    q = "How to master an agitated mind?"
    _, sysp, user = prompt_for(s, q, [q])
    chars_per_tok = (len(sysp) + len(user)) / (MEASURED_TOKENS - OVERHEAD)
finally:
    s.close()
print(f"calibration: {chars_per_tok:.2f} chars/token")

s = Searcher("bge-base")  # serving default
try:
    out["hard"] = {}
    print(
        f"\n== {label}: hard queries through retrieve_multi (bge-base, single sub-question, cap 12)"
    )
    for q, defining in HARD:
        vids, _, _ = prompt_for(s, q, [q])
        hits = [(v, i + 1) for i, v in enumerate(vids) if v in defining]
        out["hard"][q] = {"verses": vids, "defining_hits": hits}
        print(f"  {q!r}: {len(vids)} verses; defining verses in context: {hits or '-'}")
    sqs = rule_based_split(MULTI_Q)
    vids, sysp, user = prompt_for(s, MULTI_Q, sqs)
    toks = OVERHEAD + (len(sysp) + len(user)) / chars_per_tok
    out["multi"] = {
        "query": MULTI_Q,
        "sub_questions": sqs,
        "verses": vids,
        "chars": len(sysp) + len(user),
        "est_tokens": round(toks),
    }
    print(
        f"\n== {label}: 3-sub-question prompt ({len(sqs)} sub-questions): {len(vids)} verses {vids}"
    )
    print(
        f"   prompt chars {len(sysp) + len(user):,} -> ~{toks:,.0f} tokens (estimated)"
    )
finally:
    s.close()
(B / f"_scratch/concept_router_{label}.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
