"""Build a local Qdrant collection from saved embeddings.
    python indexing/build_index.py --model bge-m3
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
EMB_DIR = ROOT / "data" / "processed" / "embeddings"
QDRANT_PATH = ROOT / "qdrant_data"  # already in .gitignore
NAMESPACE = uuid.UUID("5f0c2a52-9c1e-4c7b-9f3e-6b1d2a8e4c10")  # fixed -> stable point IDs


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, chunk_id))


def collection_name(model_key: str) -> str:
    return "vyom_" + model_key.replace("-", "_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["bge-m3", "bge-base"])
    args = ap.parse_args()

    with open(CHUNKS, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]
    with open(EMB_DIR / f"{args.model}_chunk_ids.json", encoding="utf-8") as f:
        ids = json.load(f)
    vecs = np.load(EMB_DIR / f"{args.model}.npy")

    assert ids == [c["chunk_id"] for c in chunks], "chunks.jsonl changed after embedding; re-run embed.py"
    assert all("verse_id" in c for c in chunks), "every chunk needs a verse_id field"

    client = QdrantClient(path=str(QDRANT_PATH))
    name = collection_name(args.model)
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(name, vectors_config=VectorParams(size=vecs.shape[1], distance=Distance.COSINE))

    points = [
        PointStruct(id=point_id(c["chunk_id"]), vector=v.tolist(), payload=c)
        for c, v in zip(chunks, vecs)
    ]
    for i in range(0, len(points), 256):
        client.upsert(name, points[i : i + 256])
    print(f"{name}: {client.count(name).count} points, dim={vecs.shape[1]}")
    client.close()


if __name__ == "__main__":
    main()