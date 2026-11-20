"""Verify a re-index (no LLM calls): point counts, the Sanskrit-fixed verses' stored text, vectors against
the backup embeddings, and a local retrieval smoke test. Comparisons with backups are skipped when the
backup is gone. Needs the backend stopped (local Qdrant is single-process).
.\\venv\\python.exe -I backend\\scripts\\verify_reindex.py
"""

import json
import sys
from pathlib import Path

import numpy as np

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B))
sys.path.insert(0, str(B / "indexing"))
sys.stdout.reconfigure(encoding="utf-8")

from build_index import collection_name, point_id  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402

FIXED = ["1.26", "1.34", "4.29", "4.31", "9.25", "10.29"]
MODELS = ["bge-m3", "bge-base"]
verses = {}
with open(B / "data/processed/verses.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            v = json.loads(line)
            verses[v["verse_id"]] = v


def payload_sanskrit(client, model, vid):
    pts = client.retrieve(
        collection_name(model), ids=[point_id(f"{vid}:v")], with_payload=True
    )
    return pts[0].payload["payload"]["sanskrit"] if pts else None


for label, path in (
    ("BEFORE (qdrant_data.bak1)", B / "qdrant_data.bak1"),
    ("AFTER (qdrant_data)", B / "qdrant_data"),
):
    # QdrantClient(path=...) creates an empty database when the folder is missing, so never open a
    # backup that isn't there (it made an empty qdrant_data.bak1 on 2026-11-20)
    if not (path / "collection").is_dir():
        print(f"\n== {label}: not found, skipped")
        continue
    c = QdrantClient(path=str(path))
    print(f"\n== {label}")
    for m in MODELS:
        name = collection_name(m)
        n = c.count(name).count
        ok = sum(
            payload_sanskrit(c, m, vid) == verses[vid]["sanskrit"] for vid in FIXED
        )
        print(
            f"  {name}: {n} points | fixed verses matching verses.jsonl Sanskrit: {ok}/{len(FIXED)}"
        )
    c.close()

print("\n== vectors: new vs backup embeddings (same chunk order)")
for m in MODELS:
    old_path = B / f"data/processed/embeddings.bak1/{m}.npy"
    if not old_path.exists():
        print(f"  {m}: no backup embeddings at {old_path.relative_to(B)}, skipped")
        continue
    old = np.load(old_path)
    new = np.load(B / f"data/processed/embeddings/{m}.npy")
    cos = (old * new).sum(axis=1)
    print(
        f"  {m}: shape {new.shape}, min cosine(old,new)={cos.min():.6f}, max |diff|={np.abs(old - new).max():.2e}"
    )

print("\n== local retrieval (no LLM)")
from retrieval.search import Searcher  # noqa: E402

for m in MODELS:
    s = Searcher(m)
    try:
        for q in ("sthitaprajna", "How to master an agitated mind?"):
            hits = s.search(q, k=5)
            print(
                f"  [{m}] {q!r}: "
                + ", ".join(f"{h['verse_id']} ({h['score']:.3f})" for h in hits)
            )
    finally:
        s.close()

print("\n== stored text of one fixed verse, 4.29 (after)")
c = QdrantClient(path=str(B / "qdrant_data"))
print("  ", payload_sanskrit(c, "bge-m3", "4.29"))
c.close()
