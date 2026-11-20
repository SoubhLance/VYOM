"""Report mismatches between verses.jsonl (canonical), shlokaDirectory.json and verse_clips.json.

Read-only. Run from the repo root:
    .\\venv\\python.exe -I .claude/skills/sanskrit-data/check_sanskrit.py [--strict] [--verbose]
--strict exits 1 if any non-speaker text mismatch or clip problem is found.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path.cwd()
VERSES = ROOT / "backend/data/processed/verses.jsonl"
DIRECTORY = ROOT / "frontend/src/data/shlokaDirectory.json"
CLIPS = ROOT / "backend/data/multimodal/verse_clips.json"
AUDIO = ROOT / "backend/data/multimodal/source/assets/audio"

# Speaker label at the start of a verse: "अर्जुन उवाच", "श्री भगवानुवाच", "सञ्जय उवाच".
# Requires a standalone उवाच or ...भगवानुवाच so 2.10 "तमुवाच" is not stripped; the label may be glued to the verse (12.1 "उवाचएवं").
SPEAKER = re.compile(r"^\s*((?:\S+\s+){0,2}(?:उवाच|\S*भगवानुवाच))\s*")


def norm(text: str) -> str:
    """NFC, then drop whitespace, dandas, digits (Devanagari + ASCII), avagraha, nukta, | . -"""
    text = unicodedata.normalize("NFC", text or "")
    return re.sub(r"[\s।॥०-९0-9|.\-ऽ़]", "", text)


def split_speaker(text: str) -> tuple[str | None, str]:
    m = SPEAKER.match(text or "")
    if not m:
        return None, text
    return m.group(1).strip(), text[m.end() :]


def lines_of(text: str) -> list[str]:
    parts = re.split(r"[\n।॥]+", text)
    return [n for n in (norm(p) for p in parts) if n]


def main() -> int:
    strict = "--strict" in sys.argv
    verbose = "--verbose" in sys.argv
    canon = {}
    with open(VERSES, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                canon[r["verse_id"]] = r
    directory = {e["verseId"]: e for e in json.load(open(DIRECTORY, encoding="utf-8"))}
    clips = json.load(open(CLIPS, encoding="utf-8"))
    clip_lines = {
        c["clip_id"]: c["spoken_lines"] for v in clips.values() for c in v["clips"]
    }

    problems = 0
    print(
        f"verses.jsonl: {len(canon)}  shlokaDirectory: {len(directory)}  verse_clips: {len(clips)}"
    )
    for name, ids in (("shlokaDirectory", directory), ("verse_clips", clips)):
        missing, extra = sorted(set(canon) - set(ids)), sorted(set(ids) - set(canon))
        if missing or extra:
            problems += 1
            print(f"[ID] {name}: missing {missing} extra {extra}")

    speaker_only, text_diff = [], []
    for vid, e in directory.items():
        if vid not in canon:
            continue
        c = canon[vid]["sanskrit"]
        if norm(e["sanskrit"]) == norm(c):
            continue
        _, body = split_speaker(c)
        (speaker_only if norm(e["sanskrit"]) == norm(body) else text_diff).append(vid)
    print(f"[TEXT] speaker-label-only differences: {len(speaker_only)}")
    if verbose:
        print("       ", speaker_only)
    print(f"[TEXT] real text mismatches: {len(text_diff)} {text_diff}")
    problems += bool(text_diff)

    missing_files = sorted(
        c["audio_path"]
        for v in clips.values()
        for c in v["clips"]
        if not (AUDIO.parent / c["audio_path"]).exists()
    )
    print(
        f"[CLIP] verse_clips audio files missing on disk: {len(missing_files)} {missing_files[:5]}"
    )
    problems += bool(missing_files)

    dir_bad, map_bad = [], []
    for vid, r in canon.items():
        want = lines_of(split_speaker(r["sanskrit"])[1])
        if not want:
            continue
        e = directory.get(vid)
        if e:
            heard = norm("".join(clip_lines.get(e.get("clip_id"), [])))
            if not all(w in heard for w in want):
                dir_bad.append(vid)
        mapped = norm(
            "".join(
                l
                for c in clips.get(vid, {}).get("clips", [])
                for l in c["spoken_lines"]
            )
        )
        if not all(w in mapped for w in want):
            map_bad.append(vid)
    print(
        f"[CLIP] shlokaDirectory clip lacks part of its verse: {len(dir_bad)} {dir_bad}"
    )
    print(
        f"[CLIP] verse_clips mapping lacks part of its verse: {len(map_bad)} {map_bad}"
    )
    partial = [k for k, v in clips.items() if any(c.get("partial") for c in v["clips"])]
    print(f"[CLIP] verses with partial (shared) clips: {len(partial)}")
    problems += bool(dir_bad) + bool(map_bad)

    problems += check_ui(canon, verbose)
    return 1 if (strict and problems) else 0


# What the UI actually shows (since 2026-11-19): verse text from frontend/public/verses/chNN.json,
# generated from verses.jsonl by frontend/scripts/export_verses.py; shlokaDirectory only for audio.
PUBLIC_VERSES = ROOT / "frontend/public/verses"
FRONTEND_SRC = ROOT / "frontend/src"
# Same patterns as frontend/src/utils/speaker.ts
UI_SPEAKER_SA = re.compile(r"^\s*(श्री\s?भगवानुवाच|(?:अर्जुन|सञ्जय|संजय|धृतराष्ट्र)\s+उवाच)")
UI_SPEAKER_IAST = re.compile(
    r"^\s*((?:śhrī[\s-]?bhagavān|arjuna|sañjaya|dhṛitarāśhṭra|dhṛitarāśhtra)\s+uvācha)", re.I
)
# Reading verse text off a shlokaDirectory item (the reader's currentVerse, or SHLOKA_DIRECTORY directly)
DIRECTORY_TEXT_READ = re.compile(
    r"(currentVerse\??\.(sanskrit|transliteration)|SHLOKA_DIRECTORY[^;\n]*\.(sanskrit|transliteration))"
)


def check_ui(canon: dict, verbose: bool) -> int:
    shown = {}
    for path in sorted(PUBLIC_VERSES.glob("ch*.json")):
        shown.update(json.load(open(path, encoding="utf-8")))
    diff = sorted(
        vid
        for vid, r in canon.items()
        if any(shown.get(vid, {}).get(f) != (r.get(f) or "") for f in ("sanskrit", "transliteration", "word_meanings"))
    )
    print(f"[UI] public/verses verses: {len(shown)}; differing from verses.jsonl: {len(diff)} {diff[:10]}")

    readers = []
    for path in FRONTEND_SRC.rglob("*.ts*"):
        if path.suffix not in (".ts", ".tsx"):
            continue
        text = path.read_text(encoding="utf-8")
        if "recitationIndex" in text or "shlokaDirectory" in text:
            if DIRECTORY_TEXT_READ.search(text):
                readers.append(str(path.relative_to(ROOT)))
    print(f"[UI] components reading shlokaDirectory verse text: {len(readers)} {readers}")

    sa_only, iast_only = [], []
    for vid, r in canon.items():
        sa = bool(UI_SPEAKER_SA.match(unicodedata.normalize("NFC", r["sanskrit"])))
        ia = bool(UI_SPEAKER_IAST.match(unicodedata.normalize("NFC", r["transliteration"])))
        if sa and not ia:
            sa_only.append(vid)
        elif ia and not sa:
            iast_only.append(vid)
    labelled = sum(bool(UI_SPEAKER_SA.match(unicodedata.normalize("NFC", r["sanskrit"]))) for r in canon.values())
    print(
        f"[UI] speaker labels shown: {labelled}; only in Sanskrit: {len(sa_only)} {sa_only}; "
        f"only in IAST: {len(iast_only)} {iast_only}"
    )
    return bool(diff) + bool(readers)


if __name__ == "__main__":
    sys.exit(main())
