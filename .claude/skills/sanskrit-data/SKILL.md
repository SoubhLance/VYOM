---
name: sanskrit-data
description: Use whenever touching verse text, translations, shloka IDs or clip mappings (verses.jsonl, shlokaDirectory.json, recitationIndex.ts, public/translations, verse_clips.json, api/clips.py).
---

# Sources of truth

- `backend/data/processed/verses.jsonl` is canonical: 701 verses, IDs like "C.V". The backend is frozen unless the task says otherwise. After any text change the Qdrant index is stale until re-indexed.
- `backend/data/multimodal/verse_clips.json` is the only clip mapping. A verse can have 2 clips with `partial: true` (20 verses: 1.20–1.37, 4.29–4.31, 6.23–6.24). Clip file names follow the reciter's numbering, not verse IDs: `bg_01_37` is verse 1.38, and there is no `bg_01_47`.

# Generated files: never hand-edit, regenerate with their script

- `frontend/public/translations/chNN.json` ← `frontend/scripts/export_translations.py`
- `frontend/src/data/shlokaDirectory.json` ← its generator (plan step 1; not built yet)

# Rules

1. Compare Sanskrit only after normalising: NFC, then drop whitespace, dandas, numerals, avagraha and nukta (`norm()` in the check script).
2. Speaker lines ("…उवाच", "श्री भगवानुवाच", sometimes glued to the verse as in 12.1) belong in a separate `speaker` field, never in the verse text.
3. Never take verse text from a clip's `spoken_lines`; they follow the reciter's grouping.
4. Variant readings are not typos. Ask before "correcting" one (18.66 "त्वा" is a deliberate, standard reading).
5. When a fix intentionally changes a baseline number below, update the baseline here in the same task and say so in the report.

# Check

`.\venv\python.exe -I .claude/skills/sanskrit-data/check_sanskrit.py [--strict] [--verbose]` (read-only, run from the repo root).

Baseline on 2026-11-11, after the 6 typo fixes:
- speaker-label-only 58
- text mismatches 18 (17 half-verse shifts in shlokaDirectory + 18.66, where the directory has "त्वां")
- shlokaDirectory clip lacks part of its verse 15
- verse_clips mapping lacks part of its verse 0
- audio files missing 0 · partial-clip verses 20
