import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "retrieval"))

from router import load_valid_ids, parse_verse_ref


def test_router_valid_dotted():
    valid = load_valid_ids()
    assert parse_verse_ref("Verse 9.22", valid) == "9.22"
    assert parse_verse_ref("9.22", valid) == "9.22"


def test_router_invalid_chapter():
    valid = load_valid_ids()
    assert parse_verse_ref("19.3", valid) is None
    assert parse_verse_ref("chapter 19 verse 3", valid) is None


def test_router_chapter_verse_phrase():
    valid = load_valid_ids()
    assert parse_verse_ref("chapter 6, verse 5", valid) == "6.5"
    assert parse_verse_ref("Read out chapter 6, verse 5.", valid) == "6.5"
    assert parse_verse_ref("Show me chapter 4 verse 7.", valid) == "4.7"
