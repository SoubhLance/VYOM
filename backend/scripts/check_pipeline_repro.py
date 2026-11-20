"""Run the raw pipeline (clean.py -> chunk.py main) into a temp folder and compare its verses.jsonl and
chunks.jsonl byte-for-byte with data/processed. Never writes to data/processed.
    .\\venv\\python.exe -I backend\\scripts\\check_pipeline_repro.py
"""

import hashlib
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B / "ingestion"))
import chunk  # noqa: E402

PROCESSED = B / "data" / "processed"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731

with tempfile.TemporaryDirectory() as tmp:
    chunk.OUT_DIR = Path(tmp)
    chunk.main()
    ok = True
    for name in ("verses.jsonl", "chunks.jsonl"):
        a, b = PROCESSED / name, Path(tmp) / name
        same = a.read_bytes() == b.read_bytes()
        ok &= same
        print(
            f"{name}: processed {sha(a)[:16]}  pipeline {sha(b)[:16]}  byte-identical={same}"
        )
sys.exit(0 if ok else 1)
