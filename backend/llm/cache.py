"""Small in-process LRU caches for /api/ask answers and LLM splitter results.

Repeated demo questions then cost no Groq tokens. Process-local: a restart clears them.
VYOM_CACHE_SIZE sets the size of each cache (default 128); 0 turns caching off.
"""

import logging
import os
import re
import threading
from collections import OrderedDict
from typing import Any

logger = logging.getLogger("vyom.cache")


def normalize_question(text: str) -> str:
    """Casefold, collapse whitespace and drop trailing punctuation, so trivial variants share a key."""
    t = " ".join(str(text).casefold().split())
    return re.sub(r"[\s?.!]+$", "", t)


class LRUCache:
    def __init__(self, name: str, maxsize: int):
        self.name = name
        self.maxsize = maxsize
        self._data: OrderedDict[tuple, Any] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: tuple) -> Any | None:
        if self.maxsize <= 0:
            return None
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self.hits += 1
                return self._data[key]
            self.misses += 1
            return None

    def put(self, key: tuple, value: Any) -> None:
        if self.maxsize <= 0:
            return
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self.hits = 0
            self.misses = 0

    def __len__(self) -> int:
        return len(self._data)


_SIZE = int(os.getenv("VYOM_CACHE_SIZE", "128"))
ANSWER_CACHE = LRUCache("answer", _SIZE)
SPLITTER_CACHE = LRUCache("splitter", _SIZE)


def primary_model() -> str:
    """The model the answer would normally come from; part of every cache key."""
    from llm.client import (
        GROQ_MODEL,
    )  # local import: llm.client imports nothing from here

    return os.getenv("GROQ_MODEL", GROQ_MODEL)
