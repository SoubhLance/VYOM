"""Hybrid retrieval: dense (Qdrant) + BM25, fused with RRF, merged by verse_id.
    python retrieval/hybrid.py --model bge-m3 "what does sthitaprajna mean"
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "indexing"))
sys.path.insert(0, str(ROOT / "retrieval"))
sys.stdout.reconfigure(encoding="utf-8")

from search import Searcher  # noqa: E402

CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
RRF_K = 60
_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

STOPWORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "arent", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can", "cannot", "could",
    "couldn't", "couldnt", "did", "didn't", "didnt", "do", "does", "doesn't", "doesnt",
    "doing", "don't", "dont", "down", "during", "each", "few", "for", "from",
    "further", "had", "hadn't", "hadnt", "has", "hasn't", "hasnt", "have", "haven't",
    "havent", "having", "he", "he'd", "he'll", "he's", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "i'd", "i'll", "i'm", "i've",
    "if", "in", "into", "is", "isn't", "isnt", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "my", "myself", "no", "nor", "not", "of",
    "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "shouldnt", "so", "some", "such", "than", "that", "that's", "thats",
    "the", "their", "theirs", "them", "themselves", "then", "there", "these",
    "they", "they'd", "they'll", "they're", "they've", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "wasnt", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "werent", "what", "when",
    "where", "which", "while", "who", "whom", "why", "with", "won't", "wont",
    "would", "wouldn't", "wouldnt", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves",
})


def fold(text: str) -> str:
    """Lowercase and strip diacritics (ñ->n, ā->a, ṇ->n, ś->s ...)."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.replace("’", "").replace("'", "")


def tokenize(text: str):
    toks = []
    for w in _WORD.findall(fold(text)):
        parts = w.split("-")
        toks.extend(parts)
        if len(parts) > 1:
            toks.append("".join(parts))  # sthita-prajna -> also 'sthitaprajna'
    return toks


class HybridSearcher:
    def __init__(self, model_key: str, expand_always: bool = False, stopwords: bool = False):
        self.expand_always = expand_always
        self.stopwords = stopwords
        self.dense = Searcher(model_key)
        with open(CHUNKS, encoding="utf-8") as f:
            self.chunks = [json.loads(line) for line in f if line.strip()]
        corpus = [tokenize(c["embed_text"]) for c in self.chunks]
        self.bm25 = BM25Okapi(corpus)
        self.vocab = {t for doc in corpus for t in doc}

    def _expand(self, tokens):
        # A query word missing from the corpus (e.g. 'sthitaprajna' vs 'sthitaprajnasya')
        # is also matched against corpus words sharing its prefix. Handles Sanskrit inflection.
        out = []
        for t in tokens:
            out.append(t)
            if t not in self.vocab and len(t) >= 7:
                prefix = t[: max(5, len(t) - 3)]
                out.extend(sorted((w for w in self.vocab if w.startswith(prefix)), key=lambda w: (len(w), w))[:5])
        return out

    def get_bm25_scores(self, query: str, expand_always: bool | None = None, stopwords: bool | None = None):
        ea = self.expand_always if expand_always is None else expand_always
        sw = self.stopwords if stopwords is None else stopwords
        tokens = tokenize(query)
        if sw:
            filtered = [t for t in tokens if t not in STOPWORDS]
            if filtered:
                tokens = filtered
        if not ea:
            return self.bm25.get_scores(self._expand(tokens))
        else:
            term_weights = {t: 1.0 for t in tokens}
            for t in tokens:
                if len(t) >= 6:
                    for w in self.vocab:
                        if w.startswith(t) and w not in term_weights:
                            term_weights[w] = 0.5
            scores = np.zeros(len(self.chunks))
            for term, weight in term_weights.items():
                if term in self.vocab:
                    scores += weight * self.bm25.get_scores([term])
            return scores

    def search_chunks(self, query: str, n: int = 50, expand_always: bool | None = None, stopwords: bool | None = None):
        fused, vid_of = {}, {}
        for rank, (cid, vid, _) in enumerate(self.dense.search_chunks(query, n), 1):
            fused[cid] = fused.get(cid, 0.0) + 1 / (RRF_K + rank)
            vid_of[cid] = vid
        scores = self.get_bm25_scores(query, expand_always=expand_always, stopwords=stopwords)
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:n]
        for rank, i in enumerate(top, 1):
            if scores[i] <= 0:
                break
            cid = self.chunks[i]["chunk_id"]
            fused[cid] = fused.get(cid, 0.0) + 1 / (RRF_K + rank)
            vid_of[cid] = self.chunks[i]["verse_id"]
        return sorted(((cid, vid_of[cid], s) for cid, s in fused.items()), key=lambda x: -x[2])

    def search(self, query: str, k: int = 5, n_chunks: int = 50, expand_always: bool | None = None, stopwords: bool | None = None):
        verses = {}
        for cid, vid, s in self.search_chunks(query, n_chunks, expand_always=expand_always, stopwords=stopwords):  # sorted, so first chunk per verse is its best
            v = verses.setdefault(vid, {"verse_id": vid, "score": s, "chunks": []})
            v["chunks"].append((cid, round(s, 5)))
        return sorted(verses.values(), key=lambda x: -x["score"])[:k]

    def close(self):
        self.dense.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--model", default="bge-m3", choices=["bge-m3", "bge-base"])
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--expand-always", action="store_true")
    ap.add_argument("--stopwords", action="store_true")
    args = ap.parse_args()
    s = HybridSearcher(args.model, expand_always=args.expand_always, stopwords=args.stopwords)
    try:
        for r in s.search(args.query, k=args.k):
            print(f"{r['verse_id']:>7}  {r['score']:.4f}  {r['chunks']}")
    finally:
        s.close()
