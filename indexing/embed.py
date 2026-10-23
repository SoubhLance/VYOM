"""Embed chunks with a selectable local model. Run from repo root:
    python indexing/embed.py --model bge-m3 --check-only
    python indexing/embed.py --model bge-m3
    python indexing/embed.py --model bge-base
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
OUT_DIR = ROOT / "data" / "processed" / "embeddings"  # under data/processed, so already gitignored

MODELS = {
    "bge-m3": {"hf": "BAAI/bge-m3", "query_prefix": ""},
    "bge-base": {
        "hf": "BAAI/bge-base-en-v1.5",
        "query_prefix": "Represent this sentence for searching relevant passages: ",
    },
}
MAX_TOKENS = 512
DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def load_chunks():
    with open(CHUNKS, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)), "duplicate chunk_id found"
    return chunks


def token_report(chunks, key, limit):
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODELS[key]["hf"])
    enc = tok([c["embed_text"] for c in chunks], add_special_tokens=True, truncation=False)
    lens = np.array([len(x) for x in enc["input_ids"]])
    over = [(chunks[i]["chunk_id"], int(lens[i])) for i in np.where(lens > limit)[0]]
    dev = sum(1 for c in chunks if DEVANAGARI.search(c["embed_text"]))
    print(f"[{key}] tokens: median={int(np.median(lens))} p95={int(np.percentile(lens, 95))} max={int(lens.max())}")
    print(f"[{key}] over {limit} tokens (will be truncated): {len(over)}")
    for cid, n in sorted(over, key=lambda x: -x[1])[:10]:
        print(f"    {cid}: {n}")
    print(f"[{key}] chunks containing Devanagari: {dev}/{len(chunks)}")


def load_model(key, max_tokens=MAX_TOKENS):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODELS[key]["hf"])
    model.max_seq_length = max_tokens
    return model


def embed_passages(model, texts, batch_size=16):
    return model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True)


def embed_queries(model, key, queries):
    prefix = MODELS[key]["query_prefix"]
    return model.encode([prefix + q for q in queries], normalize_embeddings=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS, required=True)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--check-only", action="store_true", help="token report only, no embedding")
    args = ap.parse_args()

    chunks = load_chunks()
    token_report(chunks, args.model, args.max_tokens)
    if args.check_only:
        return

    model = load_model(args.model, args.max_tokens)
    vecs = embed_passages(model, [c["embed_text"] for c in chunks]).astype("float32")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / f"{args.model}.npy", vecs)
    with open(OUT_DIR / f"{args.model}_chunk_ids.json", "w", encoding="utf-8") as f:
        json.dump([c["chunk_id"] for c in chunks], f)
    print(f"saved {vecs.shape} to {OUT_DIR / (args.model + '.npy')}")


if __name__ == "__main__":
    main()