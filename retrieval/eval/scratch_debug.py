"""
Diagnostic script for hybrid retrieval on "What does sthitaprajna mean?"
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "retrieval"))
sys.path.insert(0, str(ROOT / "indexing"))
sys.stdout.reconfigure(encoding="utf-8")

import hybrid
from hybrid import HybridSearcher, fold, tokenize
from search import Searcher
import embed

CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"

def run_diagnostics():
    print("=" * 60)
    print("STEP 1: Inspect chunks 2.54:v, 2.54:c0, 2.55:v, 2.56:v, 2.57:v, 2.58:v")
    print("=" * 60)
    target_cids = ["2.54:v", "2.54:c0", "2.55:v", "2.56:v", "2.57:v", "2.58:v"]
    chunks_by_id = {}
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            if c["chunk_id"] in target_cids:
                chunks_by_id[c["chunk_id"]] = c
            # Also keep track if there are any other chunks for these verses
    
    search_strings = ["sthita", "prajna", "sthitaprajna", "sthitapraj"]
    
    for cid in target_cids:
        chunk = chunks_by_id.get(cid)
        if not chunk:
            print(f"Chunk {cid} NOT FOUND in chunks.jsonl!")
            continue
        embed_text = chunk["embed_text"]
        folded_text = fold(embed_text)
        print(f"\n--- Chunk {cid} ---")
        for s in search_strings:
            matches = [m.start() for m in re.finditer(re.escape(s), folded_text)]
            if matches:
                print(f"  Contains '{s}': YES ({len(matches)} match(es))")
                for idx in matches:
                    start_ctx = max(0, idx - 30)
                    end_ctx = min(len(folded_text), idx + len(s) + 30)
                    snippet = folded_text[start_ctx:end_ctx].replace("\n", " ")
                    match_str = folded_text[idx:idx+len(s)]
                    print(f"    Context: ...{snippet}...")
            else:
                print(f"  Contains '{s}': NO")

    print("\n" + "=" * 60)
    print("STEP 2: Token list from hybrid.tokenize")
    print("=" * 60)
    q_orig = "What does sthitaprajna mean?"
    toks_query = tokenize(q_orig)
    print(f"(a) Query: '{q_orig}'")
    print(f"    Tokens: {toks_query}")
    
    chunk_254v = chunks_by_id.get("2.54:v")
    if chunk_254v:
        toks_254v = tokenize(chunk_254v["embed_text"])
        print(f"(b) 2.54:v embed_text:")
        print(f"    Tokens: {toks_254v}")
    else:
        print("(b) 2.54:v NOT FOUND")

    print("\n" + "=" * 60)
    print("Initializing HybridSearcher('bge-m3')...")
    hs = HybridSearcher("bge-m3")

    gold_cids = ["2.54:v", "2.55:v", "2.56:v", "2.57:v", "2.58:v"]

    print("\n" + "=" * 60)
    print("STEP 3: BM25 only for query: 'What does sthitaprajna mean?'")
    print("=" * 60)
    # Check both raw tokens and expanded tokens for BM25
    toks_q3_raw = tokenize(q_orig)
    toks_q3_exp = hs._expand(toks_q3_raw)
    print(f"Raw tokens: {toks_q3_raw}")
    print(f"Expanded tokens used by HybridSearcher: {toks_q3_exp}")

    # Let's run with hs._expand(toks_q3_raw) as hybrid.py does
    scores_exp = hs.bm25.get_scores(toks_q3_exp)
    ranked_indices_exp = sorted(range(len(scores_exp)), key=lambda i: -scores_exp[i])

    print("\nTop 10 chunks (with hybrid.py expansion):")
    for r, i in enumerate(ranked_indices_exp[:10], 1):
        print(f"  Rank {r:>2}: {hs.chunks[i]['chunk_id']:<10} score={scores_exp[i]:.4f}")

    print("\nRank and score of 2.54:v through 2.58:v (with expansion):")
    for target in gold_cids:
        found_rank = None
        target_score = 0.0
        for r, i in enumerate(ranked_indices_exp, 1):
            if hs.chunks[i]["chunk_id"] == target:
                found_rank = r
                target_score = scores_exp[i]
                break
        if found_rank is not None and found_rank <= 100:
            print(f"  {target}: rank {found_rank}, score={target_score:.4f}")
        else:
            rank_str = f"rank {found_rank}" if found_rank else "not found"
            print(f"  {target}: not in top 100 ({rank_str}, score={target_score:.4f})")

    # Also check unexpanded raw tokens just in case
    scores_raw = hs.bm25.get_scores(toks_q3_raw)
    ranked_indices_raw = sorted(range(len(scores_raw)), key=lambda i: -scores_raw[i])
    print("\n[BM25 with raw unexpanded tokens]:")
    print("Top 10 chunks (raw unexpanded):")
    for r, i in enumerate(ranked_indices_raw[:10], 1):
        print(f"  Rank {r:>2}: {hs.chunks[i]['chunk_id']:<10} score={scores_raw[i]:.4f}")
    print("Rank and score of 2.54:v through 2.58:v (raw unexpanded):")
    for target in gold_cids:
        found_rank = None
        target_score = 0.0
        for r, i in enumerate(ranked_indices_raw, 1):
            if hs.chunks[i]["chunk_id"] == target:
                found_rank = r
                target_score = scores_raw[i]
                break
        if found_rank is not None and found_rank <= 100:
            print(f"  {target}: rank {found_rank}, score={target_score:.4f}")
        else:
            rank_str = f"rank {found_rank}" if found_rank else "not found"
            print(f"  {target}: not in top 100 ({rank_str}, score={target_score:.4f})")

    print("\n" + "=" * 60)
    print("STEP 4: BM25 only for query: 'sthitaprajna'")
    print("=" * 60)
    q_sthit = "sthitaprajna"
    toks_sthit_raw = tokenize(q_sthit)
    toks_sthit_exp = hs._expand(toks_sthit_raw)
    print(f"Raw tokens: {toks_sthit_raw}")
    print(f"Expanded tokens: {toks_sthit_exp}")

    scores_s_exp = hs.bm25.get_scores(toks_sthit_exp)
    ranked_s_exp = sorted(range(len(scores_s_exp)), key=lambda i: -scores_s_exp[i])
    print("\nTop 10 chunks (with hybrid.py expansion):")
    for r, i in enumerate(ranked_s_exp[:10], 1):
        print(f"  Rank {r:>2}: {hs.chunks[i]['chunk_id']:<10} score={scores_s_exp[i]:.4f}")
    print("\nRank and score of 2.54:v through 2.58:v (with expansion):")
    for target in gold_cids:
        found_rank = None
        target_score = 0.0
        for r, i in enumerate(ranked_s_exp, 1):
            if hs.chunks[i]["chunk_id"] == target:
                found_rank = r
                target_score = scores_s_exp[i]
                break
        if found_rank is not None and found_rank <= 100:
            print(f"  {target}: rank {found_rank}, score={target_score:.4f}")
        else:
            rank_str = f"rank {found_rank}" if found_rank else "not found"
            print(f"  {target}: not in top 100 ({rank_str}, score={target_score:.4f})")

    # Raw unexpanded for sthitaprajna
    scores_s_raw = hs.bm25.get_scores(toks_sthit_raw)
    ranked_s_raw = sorted(range(len(scores_s_raw)), key=lambda i: -scores_s_raw[i])
    print("\n[BM25 with raw unexpanded tokens]:")
    print("Top 10 chunks (raw unexpanded):")
    for r, i in enumerate(ranked_s_raw[:10], 1):
        print(f"  Rank {r:>2}: {hs.chunks[i]['chunk_id']:<10} score={scores_s_raw[i]:.4f}")
    print("Rank and score of 2.54:v through 2.58:v (raw unexpanded):")
    for target in gold_cids:
        found_rank = None
        target_score = 0.0
        for r, i in enumerate(ranked_s_raw, 1):
            if hs.chunks[i]["chunk_id"] == target:
                found_rank = r
                target_score = scores_s_raw[i]
                break
        if found_rank is not None and found_rank <= 100:
            print(f"  {target}: rank {found_rank}, score={target_score:.4f}")
        else:
            rank_str = f"rank {found_rank}" if found_rank else "not found"
            print(f"  {target}: not in top 100 ({rank_str}, score={target_score:.4f})")

    print("\n" + "=" * 60)
    print("STEP 5: IDF of each query token and chunk count (document frequency)")
    print("=" * 60)
    # Check tokens from original query, and also from expanded tokens and 'sthitaprajna'
    query_tokens_to_check = list(dict.fromkeys(toks_query + ["sthitaprajna"] + toks_sthit_exp))
    for t in query_tokens_to_check:
        idf_val = hs.bm25.idf.get(t, None)
        # Count how many chunks contain token t
        doc_count = sum(1 for doc in hs.bm25.doc_freqs if t in doc) if hasattr(hs.bm25, "doc_freqs") else sum(1 for c in hs.chunks if t in tokenize(c["embed_text"]))
        in_vocab = t in hs.vocab
        print(f"Token: '{t}' -> in_vocab={in_vocab}, IDF={idf_val}, chunk_freq={doc_count}")

    print("\n" + "=" * 60)
    print("STEP 6: Dense only (bge-m3)")
    print("=" * 60)
    # Get all dense points to find ranks beyond limit=50 if necessary
    total_chunks = len(hs.chunks)
    dense_hits_orig = hs.dense.search_chunks(q_orig, n_chunks=total_chunks)
    dense_hits_sthit = hs.dense.search_chunks(q_sthit, n_chunks=total_chunks)

    print(f"Dense rank for query '{q_orig}':")
    dense_ranks_orig = {cid: (rank, score) for rank, (cid, vid, score) in enumerate(dense_hits_orig, 1)}
    for vid in ["2.54", "2.55", "2.56", "2.57", "2.58"]:
        # Also check verse chunks
        v_matches = [(cid, r, s) for cid, (r, s) in dense_ranks_orig.items() if cid.startswith(vid + ":")]
        v_matches.sort(key=lambda x: x[1])
        print(f"  Verse {vid}: best chunk {v_matches[0] if v_matches else 'NONE'} (all chunks: {v_matches})")

    print(f"\nDense rank for query '{q_sthit}':")
    dense_ranks_sthit = {cid: (rank, score) for rank, (cid, vid, score) in enumerate(dense_hits_sthit, 1)}
    for vid in ["2.54", "2.55", "2.56", "2.57", "2.58"]:
        v_matches = [(cid, r, s) for cid, (r, s) in dense_ranks_sthit.items() if cid.startswith(vid + ":")]
        v_matches.sort(key=lambda x: x[1])
        print(f"  Verse {vid}: best chunk {v_matches[0] if v_matches else 'NONE'} (all chunks: {v_matches})")

    print("\n" + "=" * 60)
    print("STEP 7: Fused hybrid for both queries & RRF breakdown for 2.54")
    print("=" * 60)
    def analyze_hybrid(q):
        print(f"\n--- Fused Hybrid for: '{q}' ---")
        fused = {}
        bm25_contrib = {}
        dense_contrib = {}
        vid_of = {}

        # Dense
        dense_top50 = hs.dense.search_chunks(q, n_chunks=50)
        for rank, (cid, vid, _) in enumerate(dense_top50, 1):
            rrf_d = 1.0 / (hybrid.RRF_K + rank)
            dense_contrib[cid] = (rank, rrf_d)
            fused[cid] = fused.get(cid, 0.0) + rrf_d
            vid_of[cid] = vid

        # BM25
        exp_tokens = hs._expand(tokenize(q))
        scores = hs.bm25.get_scores(exp_tokens)
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:50]
        for rank, i in enumerate(top, 1):
            if scores[i] <= 0:
                break
            cid = hs.chunks[i]["chunk_id"]
            rrf_b = 1.0 / (hybrid.RRF_K + rank)
            bm25_contrib[cid] = (rank, rrf_b)
            fused[cid] = fused.get(cid, 0.0) + rrf_b
            vid_of[cid] = hs.chunks[i]["verse_id"]

        sorted_fused = sorted(((cid, vid_of[cid], s) for cid, s in fused.items()), key=lambda x: -x[2])
        print("Final top 10 chunks:")
        for r, (cid, vid, s) in enumerate(sorted_fused[:10], 1):
            b_info = bm25_contrib.get(cid, ("-", 0.0))
            d_info = dense_contrib.get(cid, ("-", 0.0))
            print(f"  Rank {r:>2}: {cid:<10} vid={vid:<6} fused_score={s:.5f} (Dense: rank {d_info[0]}, RRF={d_info[1]:.5f} | BM25: rank {b_info[0]}, RRF={b_info[1]:.5f})")

        # Verses top 10
        verse_fused = {}
        for cid, vid, s in sorted_fused:
            v = verse_fused.setdefault(vid, {"verse_id": vid, "score": s, "chunks": []})
            v["chunks"].append((cid, round(s, 5)))
        top_verses = sorted(verse_fused.values(), key=lambda x: -x["score"])[:10]
        print("Final top 10 verses:")
        for r, v in enumerate(top_verses, 1):
            print(f"  Rank {r:>2}: {v['verse_id']:>6}  score={v['score']:.5f}  chunks={v['chunks']}")

        print("\nRRF contribution for 2.54 chunks:")
        for cid in sorted([c for c in fused if c.startswith("2.54")] + [c for c in ["2.54:v", "2.54:c0"] if c not in fused]):
            d_rank, d_rrf = dense_contrib.get(cid, ("not in top 50", 0.0))
            b_rank, b_rrf = bm25_contrib.get(cid, ("not in top 50", 0.0))
            tot = fused.get(cid, 0.0)
            print(f"  {cid}: Dense rank={d_rank} (RRF={d_rrf:.5f}), BM25 rank={b_rank} (RRF={b_rrf:.5f}), Total RRF={tot:.5f}")

    analyze_hybrid(q_orig)
    analyze_hybrid(q_sthit)

    print("\n" + "=" * 60)
    print("STEP 8: Prefix expansion check")
    print("=" * 60)
    for q in [q_orig, q_sthit]:
        toks = tokenize(q)
        exp = hs._expand(toks)
        applied = (exp != toks)
        print(f"Query: '{q}'")
        print(f"  Is prefix expansion applied? {applied}")
        print(f"  Original tokens: {toks}")
        print(f"  Expanded tokens: {exp}")
        for t in toks:
            print(f"    Token '{t}': in_vocab={t in hs.vocab}, len={len(t)}")
            if t not in hs.vocab and len(t) >= 7:
                pfx = t[: max(5, len(t) - 3)]
                matching = sorted((w for w in hs.vocab if w.startswith(pfx)), key=lambda w: (len(w), w))[:5]
                print(f"      prefix='{pfx}', matches={matching}")

    hs.close()

def run_part_c():
    print("\n" + "=" * 60)
    print("PART C.1: Check expansion explosion (> 15 words) for 24 questions")
    print("=" * 60)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]
    corpus = [tokenize(c["embed_text"]) for c in chunks]
    vocab = {t for doc in corpus for t in doc}

    questions_path = ROOT / "retrieval" / "eval" / "questions.jsonl"
    with open(questions_path, encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    all_tokens_exp = {}
    exploded = []
    for q in questions:
        toks = tokenize(q["q"])
        for t in toks:
            if len(t) >= 6 and t not in all_tokens_exp:
                exp = sorted([w for w in vocab if w.startswith(t)])
                all_tokens_exp[t] = exp
                if len(exp) > 15:
                    exploded.append((t, exp))

    print(f"Total questions: {len(questions)}")
    print(f"Total unique tokens of length >= 6: {len(all_tokens_exp)}")
    print(f"Tokens expanding to > 15 vocab words: {len(exploded)}")
    if exploded:
        for t, exp in exploded:
            print(f"  Token '{t}' ({len(exp)} expansions): {exp}")
    else:
        print("No tokens expanded to > 15 vocab words.")
        print("Summary of all token expansion counts:")
        for t, exp in sorted(all_tokens_exp.items(), key=lambda x: (-len(x[1]), x[0])):
            print(f"  {t:<15} -> {len(exp):>2} expansions: {exp}")

    print("\n" + "=" * 60)
    print("PART C.2: BM25-only top 10 chunks and ranks under 4 configs")
    print("=" * 60)
    hs = HybridSearcher("bge-m3")
    q = "What does sthitaprajna mean?"
    configs = [
        ("baseline", False, False),
        ("--stopwords", False, True),
        ("--expand-always", True, False),
        ("both", True, True),
    ]
    for cfg_name, ea, sw in configs:
        scores = hs.get_bm25_scores(q, expand_always=ea, stopwords=sw)
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
        cids = [hs.chunks[i]["chunk_id"] for i in ranked]
        print(f"\n--- Config: {cfg_name} ---")
        print("Top 10 chunks:")
        for r, i in enumerate(ranked[:10], 1):
            print(f"  Rank {r:>2}: {cids[r-1]:<10} score={scores[i]:.4f}")
        for target in ["2.54:v", "2.55:v"]:
            idx = cids.index(target) + 1
            sc = scores[ranked[idx - 1]]
            if idx <= 100:
                print(f"  {target}: rank {idx}, score={sc:.4f}")
            else:
                print(f"  {target}: not in top 100 (rank {idx}, score={sc:.4f})")
    hs.close()

if __name__ == "__main__":
    run_part_c()

