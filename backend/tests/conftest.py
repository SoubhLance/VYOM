import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Ensure backend root and submodules are accessible on sys.path
for path_entry in [
    BACKEND_DIR,
    BACKEND_DIR / "ingestion",
    BACKEND_DIR / "retrieval",
    BACKEND_DIR / "indexing",
    BACKEND_DIR / "api",
    BACKEND_DIR / "llm",
]:
    p_str = str(path_entry)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_llm_caches():
    """The answer and splitter LRU caches are process-wide; start every test empty."""
    from llm.cache import ANSWER_CACHE, SPLITTER_CACHE

    ANSWER_CACHE.clear()
    SPLITTER_CACHE.clear()
    yield
    ANSWER_CACHE.clear()
    SPLITTER_CACHE.clear()
