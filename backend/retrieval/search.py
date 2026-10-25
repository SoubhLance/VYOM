"""Query -> embed -> top-N chunks -> merge by verse_id -> top-k verses.
    python retrieval/search.py --model bge-m3 "how do I control a restless mind"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "indexing"))
sys.stdout.reconfigure(encoding="utf-8")

from build_index import QDRANT_PATH, collection_name  # noqa: E402
from embed import embed_queries, load_model  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402


class Searcher:
    # Qdrant local mode allows one client per path, so create ONE Searcher per model and reuse it.
    def __init__(self, model_key: str):
        self.key = model_key
        self.model = load_model(model_key)
        self.client = QdrantClient(path=str(QDRANT_PATH))
        self.collection = collection_name(model_key)

    def search(self, query: str, k: int = 5, n_chunks: int = 30):
        qv = embed_queries(self.model, self.key, [query])[0].tolist()
        hits = self.client.query_points(
            self.collection, query=qv, limit=n_chunks, with_payload=True
        ).points
        verses = {}
        for h in hits:  # hits come sorted by score; first hit per verse is its best
            vid = h.payload["verse_id"]
            v = verses.setdefault(vid, {"verse_id": vid, "score": h.score, "chunks": []})
            v["chunks"].append((h.payload["chunk_id"], round(h.score, 4)))
        return sorted(verses.values(), key=lambda x: -x["score"])[:k]

    def search_chunks(self, query: str, n_chunks: int = 50):
        qv = embed_queries(self.model, self.key, [query])[0].tolist()
        hits = self.client.query_points(
            self.collection, query=qv, limit=n_chunks, with_payload=True
        ).points
        return [(h.payload["chunk_id"], h.payload["verse_id"], h.score) for h in hits]

    def close(self):
        self.client.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--model", default="bge-m3", choices=["bge-m3", "bge-base"])
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()
    s = Searcher(args.model)
    try:
        for r in s.search(args.query, k=args.k):
            print(f"{r['verse_id']:>7}  {r['score']:.4f}  {r['chunks']}")
    finally:
        s.close()