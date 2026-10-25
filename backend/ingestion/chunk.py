import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from clean import load_clean, EMBED_MIN_COMMENTARY_CHARS
from load import load_chapters

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

# Verse-chunk config (tune via eval)
EMBED_TRANSLATORS = [
    "Swami Sivananda", "Swami Gambirananda", "Swami Adidevananda", "Shri Purohit Swami",
]
INCLUDE_WORD_MEANINGS = False

# Commentary-chunk config
COMM_MAX_CHARS = 1200          # ~300 tokens
COMM_OVERLAP_SENTENCES = 1
SENT_SPLIT = re.compile(r'(?<=[.!])\s+(?=[A-Z"“(])')


# ---------- splitting ----------

def _hard_split(s: str, max_chars: int) -> list[str]:
    """Fallback for a 'sentence' longer than max_chars: split on words."""
    out, cur = [], ""
    for w in s.split():
        if cur and len(cur) + 1 + len(w) > max_chars:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def split_text(text: str, max_chars: int = COMM_MAX_CHARS,
               overlap: int = COMM_OVERLAP_SENTENCES) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sents = []
    for s in SENT_SPLIT.split(text):
        sents.extend(_hard_split(s, max_chars) if len(s) > max_chars else [s])

    chunks, cur = [], []
    for s in sents:
        if cur and len(" ".join(cur + [s])) > max_chars:
            chunks.append(" ".join(cur))
            cur = cur[-overlap:] if overlap else []
            if cur and len(" ".join(cur + [s])) > max_chars:
                cur = []                       # overlap too big, drop it
        cur.append(s)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


# ---------- embed text ----------

def verse_embed_text(v: dict, chapter_name: str) -> str:
    by_author = {t["author"]: t["text"] for t in v["translations"]["english"]}
    texts, seen = [], set()
    for a in EMBED_TRANSLATORS:
        t = by_author.get(a)
        if t and t not in seen:
            texts.append(t)
            seen.add(t)
    if not texts:                              # fallback: whatever English exists
        texts = [t["text"] for t in v["translations"]["english"][:4]]

    parts = [f'Bhagavad Gita {v["verse_id"]} — {chapter_name}', *texts,
             v["transliteration"].replace("\n", " / ")]
    if INCLUDE_WORD_MEANINGS:
        parts.append(v["word_meanings"])
    return "\n".join(parts)


# ---------- build ----------

def build_chunks():
    verses = load_clean()
    chap = {c["chapter_number"]: (c.get("name_translated") or c.get("name_transliterated")
                                  or c.get("name") or f'Chapter {c["chapter_number"]}')
            for c in load_chapters()}

    chunks = []
    for v in verses:
        vid, ch_name = v["verse_id"], chap[v["chapter"]]
        base = {"verse_id": vid, "chapter": v["chapter"], "verse": v["verse"]}

        chunks.append({
            "chunk_id": f"{vid}:v",
            "verse_id": vid,
            "type": "verse",
            "embed_text": verse_embed_text(v, ch_name),
            "payload": {**base, "type": "verse",
                        "sanskrit": v["sanskrit"], "transliteration": v["transliteration"]},
        })

        for c in v["commentaries"]:
            if c["author"] != "Swami Sivananda" or c["language"] != "english":
                continue
            if len(c["text"]) < EMBED_MIN_COMMENTARY_CHARS:
                continue
            parts = split_text(c["text"])
            for i, part in enumerate(parts):
                chunks.append({
                    "chunk_id": f"{vid}:c{i}",
                    "verse_id": vid,
                    "type": "commentary",
                    "embed_text": f"Sivananda commentary on Bhagavad Gita {vid} ({ch_name}): {part}",
                    "payload": {**base, "type": "commentary", "author": "Swami Sivananda",
                                "part": i, "parts": len(parts), "text": part},
                })
    return verses, chunks


def main():
    verses, chunks = build_chunks()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_DIR / "verses.jsonl", "w", encoding="utf-8") as f:
        for v in verses:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")
    with open(OUT_DIR / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    vc = [c for c in chunks if c["type"] == "verse"]
    cc = [c for c in chunks if c["type"] == "commentary"]
    L = sorted(len(c["embed_text"]) for c in chunks)
    print(f"verse chunks: {len(vc)} | commentary chunks: {len(cc)} "
          f"(from {len({c['verse_id'] for c in cc})} verses) | total: {len(chunks)}")
    print(f"embed_text chars: median={L[len(L)//2]} p95={L[int(len(L)*.95)]} max={L[-1]}")
    print(f"multi-part commentaries: {sum(1 for c in cc if c['payload']['part'] == 0 and c['payload']['parts'] > 1)}")
    ex = next(c for c in chunks if c["chunk_id"] == "2.47:v")
    print("\n--- 2.47 verse embed_text ---\n" + ex["embed_text"])


if __name__ == "__main__":
    main()