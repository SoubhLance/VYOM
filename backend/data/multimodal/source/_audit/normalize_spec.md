# Specification: Gita Verse Data Normalization

## Context & Motivation
An audit of the 18 `verses.json` files under `backend/data/gita/<NN>/verses.json` revealed three recurring data hygiene defects:
1. **Stray Nukta (`U+093C`):** Found in 4 verses across chapters 1, 4, 9, and 10 (e.g., `पितृ़नथ`, `कुतो़ऽन्यः`, `पितृ़न्यान्ति`, `पितृ़णामर्यमा`). In standard Devanagari Sanskrit orthography, nukta is inappropriate here and corrupts text search, exact string matching, and embeddings.
2. **Glued Speaker Labels:** Found in 11 verses (prominently in Ch 12, 13, 14, e.g., `अर्जुन उवाचएवं...`, `श्री भगवानुवाचइदं...`). The speaker introduction string lacks separating whitespace or a distinct schema attribute, corrupting verse text indexing and multimodal alignment.
3. **Missing Line Breaks:** Found in 222 verses where both hemistichs (halves of the shloka) are concatenated into a single string rather than separated into distinct lines.

This document specifies the exact transformation pipeline to clean and normalize all verse records into a consistent, robust JSON schema without altering authentic Sanskrit readings.

---

## Target JSON Schema

Each entry in `backend/data/gita/<chapter>/verses.json` should conform to:

```json
{
  "chapter": 13,
  "verse_number": 2,
  "speaker": "श्रीभगवानुवाच",
  "lines": [
    "इदं शरीरं कौन्तेय क्षेत्रमित्यभिधीयते।",
    "एतद्यो वेत्ति तं प्राहुः क्षेत्रज्ञ इति तद्विदः।।13.2।।"
  ],
  "text": [
    "इदं शरीरं कौन्तेय क्षेत्रमित्यभिधीयते।",
    "एतद्यो वेत्ति तं प्राहुः क्षेत्रज्ञ इति तद्विदः।।13.2।।"
  ],
  "full_verse": "इदं शरीरं कौन्तेय क्षेत्रमित्यभिधीयते।\nएतद्यो वेत्ति तं प्राहुः क्षेत्रज्ञ इति तद्विदः।।13.2।।"
}
```

### Fields:
- `chapter` (int): 1 to 18.
- `verse_number` (int): Verse index within the chapter.
- `speaker` (string | null): The speaker label if the verse contains a dialogue attribution (e.g., `"धृतराष्ट्र उवाच"`, `"सञ्जय उवाच"`, `"अर्जुन उवाच"`, `"श्रीभगवानुवाच"`), otherwise `null`.
- `lines` (list of strings): Array of non-empty verse lines (typically 2 for Anushtubh metre, 3-4 for Trishtubh/Jagati or split metre), stripped of leading speaker labels and trailing/leading whitespace.
- `text` (list of strings): Retained for backwards-compatibility with existing loaders, pointing to the same cleaned line list.
- `full_verse` (string): Standard newline-delimited canonical string.

---

## Transformation Pipeline

For each verse record in chapter `c`:

### Step 1: Strip Stray Combining Marks (Nukta)
- Remove all instances of Unicode codepoint `\u093C` (`DEVANAGARI SIGN NUKTA`).
- Python equivalent:
  ```python
  raw_text = raw_text.replace('\u093c', '')
  ```

### Step 2: Speaker Label Extraction & Isolation
Recognize known Gita speaker formulas:
- `धृतराष्ट्र उवाच` / `धृतराष्ट्र उवाच:`
- `सञ्जय उवाच` / `सञ्जय उवाच:`
- `अर्जुन उवाच` / `अर्जुन उवाच:`
- `श्रीभगवानुवाच` / `श्री भगवानुवाच` / `भगवानुवाच`

Extraction logic:
- Check if text begins with any recognized speaker pattern (with or without internal space, optional trailing visarga, danda, colon, or whitespace).
- If matched:
  1. Extract canonical speaker representation (standardized to `"धृतराष्ट्र उवाच"`, `"सञ्जय उवाच"`, `"अर्जुन उवाच"`, `"श्रीभगवानुवाच"`).
  2. Strip the matched prefix completely from the verse body.

### Step 3: Hemistich / Line Segmentation
Many verses currently collapse two lines into one line containing `।` and `॥` (or `।।`).
To reliably split into proper verse lines:
1. Normalize danda punctuation:
   - Double danda variants (`।।`, `॥`, `||`) at the end of the first half (rare) or second half (standard).
   - Single danda (`।`, `|`) marking the caesura (half-shloka).
2. If the verse contains a single line with an internal single danda `।`:
   - Split after the first single danda:
     ```python
     if len(lines) == 1 and '।' in lines[0]:
         parts = re.split(r'(?<=।)\s*', lines[0])
         lines = [p.strip() for p in parts if p.strip()]
     ```
3. Ensure each line retains its terminating punctuation (`।` on line 1, `॥` or `।।` on line 2).

### Step 4: Whitespace and Digit Normalization
- Strip leading and trailing whitespace on each line.
- Collapse multiple consecutive spaces into a single space.
- Preserve colophon numbers (e.g. `।।13.2।।`) at the verse end, or optionally standardize them into canonical Devanagari numerals.

---

## Verification & Invariants
After running the normalization spec (when approved):
1. No character `\u093c` exists in any `verses.json`.
2. Every verse with dialogue has `speaker` populated in its own dedicated field, and no speaker formula appears inside `lines`.
3. Exactly zero verses have missing line breaks (each shloka has $\ge 2$ lines).
4. No empty lines or verses with $< 20$ characters.
5. All original words, sandhi, and semantics are 100% preserved.

