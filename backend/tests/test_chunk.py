import json
import re
from pathlib import Path
import pytest

from chunk import build_chunks, split_text, verse_embed_text

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
CHUNKS_FILE = DATA_DIR / "chunks.jsonl"
VERSES_FILE = DATA_DIR / "verses.jsonl"


@pytest.fixture(scope="module")
def chunks():
    assert CHUNKS_FILE.exists(), f"Missing {CHUNKS_FILE}"
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.fixture(scope="module")
def verses():
    assert VERSES_FILE.exists(), f"Missing {VERSES_FILE}"
    with open(VERSES_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_exactly_701_verse_chunks(chunks):
    """Assert exactly 701 verse chunks (<verse_id>:v) exist."""
    verse_chunks = [c for c in chunks if c.get("chunk_id", "").endswith(":v")]
    assert len(verse_chunks) == 701, f"Expected 701 verse chunks, got {len(verse_chunks)}"
    for c in verse_chunks:
        assert c.get("type") == "verse"
        assert c["chunk_id"] == f"{c['verse_id']}:v"


def test_all_chunk_ids_unique(chunks):
    """Assert all chunk_ids across chunks.jsonl are unique."""
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)), f"Duplicate chunk_ids found: {len(ids) - len(set(ids))} duplicates"


def test_commentary_base_verse_ids_exist(chunks, verses):
    """Assert every commentary chunk's base verse_id exists in verses.jsonl."""
    verse_ids = {v["verse_id"] for v in verses}
    comm_chunks = [c for c in chunks if c.get("type") == "commentary"]
    assert len(comm_chunks) > 0, "No commentary chunks found"
    for c in comm_chunks:
        assert c["verse_id"] in verse_ids, f"Commentary chunk {c['chunk_id']} has unknown verse_id {c['verse_id']}"


def test_no_empty_or_whitespace_embed_text(chunks):
    """Assert no chunk has empty or whitespace-only embed_text."""
    for c in chunks:
        embed_text = c.get("embed_text")
        assert embed_text is not None, f"Chunk {c.get('chunk_id')} missing embed_text"
        assert embed_text.strip() != "", f"Chunk {c.get('chunk_id')} has empty/whitespace embed_text"


def test_no_embed_text_exceeds_1500_chars(chunks):
    """Assert no embed_text exceeds 1,500 characters."""
    for c in chunks:
        text_len = len(c.get("embed_text", ""))
        assert text_len <= 1500, f"Chunk {c['chunk_id']} exceeds 1500 chars (length: {text_len})"


def test_no_leftover_editorial_labels(chunks):
    """Assert no leftover editorial labels (e.g., 'Fix:', 'Corrected:') remain in embed_text."""
    pattern = re.compile(r"\b(Fix:|Fixed:|Corrected:|Correction:|Revised:)", re.IGNORECASE)
    for c in chunks:
        match = pattern.search(c["embed_text"])
        assert not match, f"Found editorial label '{match.group()}' in chunk {c['chunk_id']}: {c['embed_text']}"


def test_chunking_deterministic(chunks):
    """Assert chunking is deterministic across multiple executions."""
    # 1. Test split_text determinism
    sample_text = (
        "This is the first sentence. Here is the second sentence that contains detailed philosophical discussion. "
        "And a third sentence elaborating on the duties and nature of the self. "
        "Finally, the fourth sentence concludes this passage."
    )
    splits_1 = split_text(sample_text, max_chars=100, overlap=1)
    splits_2 = split_text(sample_text, max_chars=100, overlap=1)
    assert splits_1 == splits_2

    # 2. Test build_chunks determinism against saved chunks
    _, freshly_built_chunks = build_chunks()
    assert freshly_built_chunks == chunks
