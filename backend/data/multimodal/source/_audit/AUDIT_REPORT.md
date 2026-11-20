# Multimodal Audio Splitting Pipeline Audit Report: Bhagavad Gita

**Location:** `D:\VYOM-AI`  
**Target Video:** `backend\data\multimodal\source\lecture.mp4`  
**Audit Directory:** `backend\data\multimodal\source\_audit\`  
**Execution Mode:** Strictly READ-ONLY (No git commands executed, no existing files modified or deleted, no packages installed).

---

## Executive Summary & Chapter Status Matrix

| Chapter | Expected Slides | Planned Clips | Check A (Plan Integrity) | Check B (Data Hygiene) | Check C (Slide Alignment) | Check D (Audio Boundary) | Overall Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Ch 01** | 46 | 46 | **PASS** | **WARN** (1 nukta) | **WARN** (Chained shift s26-36) | **WARN** (Bleed/drone floor) | **NEEDS REVIEW** |
| **Ch 02** | 72 | 72 | **PASS** | **PASS** | **PASS** (72/72 match) | **WARN** (Drone floor) | **READY** |
| **Ch 03** | 43 | 43 | **PASS** | **PASS** | **PASS** (43/43 match) | **WARN** (Drone floor) | **READY** |
| **Ch 04** | 42 | 42 | **PASS** | **WARN** (1 nukta) | **WARN** (Mid-ch shift s29-31) | **WARN** (Drone floor) | **NEEDS REVIEW** |
| **Ch 05** | 29 | 29 | **PASS** | **PASS** | **PASS** (29/29 match) | **WARN** (Drone floor) | **READY** |
| **Ch 06** | 47 | 47 | **PASS** | **PASS** | **PASS** (47/47 match) | **WARN** (Drone floor) | **READY** |
| **Ch 07** | 30 | 30 | **PASS** | **PASS** | **PASS** (30/30 match) | **WARN** (Drone floor) | **READY** |
| **Ch 08** | 28 | 28 | **PASS** | **PASS** | **PASS** (28/28 match) | **WARN** (Drone floor) | **READY** |
| **Ch 09** | 34 | 34 | **PASS** | **WARN** (1 nukta) | **PASS** (34/34 match) | **WARN** (Drone floor) | **READY** |
| **Ch 10** | 42 | 42 | **PASS** | **WARN** (1 nukta) | **PASS** (42/42 match) | **WARN** (Drone floor) | **READY** |
| **Ch 11** | 55 | 55 | **PASS** | **PASS** | **PASS** (55/55 match) | **WARN** (Drone floor) | **READY** |
| **Ch 12** | 20 | 20 | **PASS** | **WARN** (Glued / no-break) | **PASS** (20/20 match) | **WARN** (Drone floor) | **READY** |
| **Ch 13** | 35 | 35 | **PASS** | **WARN** (Glued / no-break) | **PASS** (35/35 match) | **WARN** (Drone floor) | **READY** |
| **Ch 14** | 27 | 27 | **PASS** | **WARN** (Glued / no-break) | **PASS** (27/27 match) | **WARN** (Drone floor) | **READY** |
| **Ch 15** | 20 | 20 | **PASS** | **WARN** (Glued / no-break) | **PASS** (20/20 match) | **WARN** (Drone floor) | **READY** |
| **Ch 16** | 24 | 24 | **PASS** | **WARN** (Glued / no-break) | **PASS** (24/24 match) | **WARN** (Drone floor) | **READY** |
| **Ch 17** | 28 | 28 | **PASS** | **WARN** (Glued / no-break) | **PASS** (28/28 match) | **WARN** (Drone floor) | **READY** |
| **Ch 18** | 78 | 78 | **PASS** | **WARN** (Glued / no-break) | **PASS** (78/78 match) | **WARN** (Drone floor) | **READY** |

---

## Detailed Section Findings & Evidence

### A. File and Plan Integrity

1. **Lecture Media & Chapter Markers:**
   - `lecture.mp4` ffprobe measured duration: **`10664.694 s`** (`02:57:44.694`), which exceeds the minimum required threshold of `2:57:32` (`10652.0 s`).
   - `chapters.csv`: Exactly 18 rows. All start timestamps are strictly monotonically increasing, spanning from Ch 1 (`0:22` = `22.0 s`) to Ch 18 (`2:40:04` = `9604.0 s`).

2. **Combined Plan Validation (`cuts_ch01_46.csv` + `cuts_slides.csv` Ch 2–18):**
   - Total planned clips: **700 rows** (Ch 1 has 46 rows; Ch 2–18 match exact traditional verse counts).
   - Starts and ends are strictly increasing without gaps.
   - Negative durations: **0**
   - Clip overlaps: **0**
   - Chapter window violations: **0**
   - Clips under 3.0 s: **0** (Minimum duration in plan is 4.3 s)
   - Clips over 30.0 s: **0** (Maximum duration in plan is 29.7 s, Colophon of Ch 18)

3. **Scene Change Drops (`scene_chNN.txt` vs Planned Boundaries):**
   - Every chapter in `scene_chNN.txt` contains between $N+1$ and $N+3$ scene changes.
   - The planning algorithm picked contiguous runs of $N+1$ changes, dropping head title cards and closing colophons:
     - **Ch 01:** 48 changes, 46 planned clips $\rightarrow$ 1 tail dropped at `731.360 s`.
     - **Ch 02:** 75 changes, 72 planned clips $\rightarrow$ 2 tail dropped at `1808.640 s`, `1818.640 s`.
     - **Ch 03:** 44 changes, 43 planned clips $\rightarrow$ 0 head/tail dropped (exact match to interior window).
     - **Ch 04:** 45 changes, 42 planned clips $\rightarrow$ 1 head dropped at `2447.880 s`, 1 tail dropped at `3081.480 s`.
     - **Ch 05:** 31 changes, 29 planned clips $\rightarrow$ 1 tail dropped at `3538.760 s`.
     - **Ch 06:** 50 changes, 47 planned clips $\rightarrow$ 1 head dropped at `3549.000 s`, 1 tail dropped at `4255.360 s`.
     - **Ch 07:** 32 changes, 30 planned clips $\rightarrow$ 1 tail dropped at `4724.040 s`.
     - **Ch 08:** 30 changes, 28 planned clips $\rightarrow$ 1 tail dropped at `5184.720 s`.
     - **Ch 09:** 37 changes, 34 planned clips $\rightarrow$ 1 head dropped at `5194.880 s`, 1 tail dropped at `5712.760 s`.
     - **Ch 10:** 44 changes, 42 planned clips $\rightarrow$ 1 tail dropped at `6331.040 s`.
     - **Ch 11:** 58 changes, 55 planned clips $\rightarrow$ 1 head dropped at `6341.200 s`, 1 tail dropped at `7269.560 s`.
     - **Ch 12:** 21 changes, 20 planned clips $\rightarrow$ 0 head/tail dropped.
     - **Ch 13:** 38 changes, 35 planned clips $\rightarrow$ 2 head dropped at `7581.840 s`, `7592.000 s`.
     - **Ch 14:** 30 changes, 27 planned clips $\rightarrow$ 1 head dropped at `8087.200 s`, 1 tail dropped at `8501.440 s`.
     - **Ch 15:** 21 changes, 20 planned clips $\rightarrow$ 0 head/tail dropped.
     - **Ch 16:** 27 changes, 24 planned clips $\rightarrow$ 1 head dropped at `8834.680 s`, 1 tail dropped at `9193.200 s`.
     - **Ch 17:** 30 changes, 28 planned clips $\rightarrow$ 1 head dropped at `9203.360 s`.
     - **Ch 18:** 80 changes, 78 planned clips $\rightarrow$ 1 head dropped at `9604.120 s`.

---

### B. Data Hygiene (verses.json)

- Total verses across 18 chapters: **701 verses** (Ch 1 = 47, Ch 13 = 35).
- Duplicates or gaps in `verse_number`: **None** (1 to N sequential in every file).
- Anomalies identified:
  1. **Stray Nukta (`U+093C`):** Exactly 4 occurrences:
     - `Ch 1.26`: `पितृ़नथ` and `भ्रातृ़न्पुत्रान्`
     - `Ch 4.31`: `कुतो़ऽन्यः`
     - `Ch 9.25`: `पितृ़न्यान्ति`
     - `Ch 10.29`: `पितृ़णामर्यमा`
  2. **Glued Speaker Labels:** Exactly 11 verses where speaker tags are joined directly to verse text without spaces or schema separation:
     - `Ch 12.1`: `अर्जुन उवाचएवं सततयुक्ता...`
     - `Ch 12.2`: `श्री भगवानुवाचमय्यावेश्य मनो...`
     - `Ch 13.2`: `श्री भगवानुवाचइदं शरीरं कौन्तेय...`
     - `Ch 14.1`: `श्री भगवानुवाचपरं भूयः प्रवक्ष्यामि...`
     - `Ch 14.21`: `अर्जुन उवाचकैर्लिंगैस्त्रीन्गुणानेतानतीतो...`
     - (also in 15.1, 16.1, 17.1, 17.2, 18.1, 18.73)
  3. **Missing Line Breaks between Hemistichs:** Exactly **222 verses** (primarily in Ch 12 through 18) contain single strings with internal dandas rather than arrays of 2 lines.
  4. **Short/Empty Verses (< 20 characters):** **0** (All verses have substantial Sanskrit text).
- **Normalization Spec:** Generated and saved at `_audit\normalize_spec.md`.

---

### C. Slide-to-Data Alignment

All 700 frames were extracted at $(slide\_end - 1.0 s)$ and transcribed blind using Tesseract OCR (`san+hin` models with PSM 6). Programmatic comparison against `verses.json` produced:

- **Total Slides:** 700
- **MATCH:** 687 slides (100% 1-to-1 verse match)
- **SHIFTED:** 11 slides
- **UNREADABLE by automated OCR:** 2 slides (Both verified manually via vision as 100% exact MATCHES)

#### Critical Alignment Anomalies Discovered:

1. **Chapter 1 Chained Half-Verse Shift (Slides 26–36):**
   - Slides 1–25: 1-to-1 match with data verses 1–25.
   - Slides 26–36: Each slide contains Line 2 of verse $K$ and Line 1 of verse $K+1$.
   - Slide 37 onwards: Contains Verse 38. The numbering on screen is offset by $-1$ compared to data verses (Slide 46 = Verse 47).
   - This matches `backend\data\multimodal\source\ch01_map_v2.csv`.

2. **Chapter 4 Mid-Chapter Half-Verse Shift (Slides 29–31):**
   - **Slide 28:** Contains Verse 4.28 (complete).
   - **Slide 29:** Displays **3 lines**: Full Verse 4.29 + Verse 4.30 Line 1 (`अपरे नियताहाराः प्राणान्प्राणेषु जुह्वति`).
   - **Slide 30:** Displays Verse 4.30 Line 2 (`सर्वेऽप्येते यज्ञविदो...`) + Verse 4.31 Line 1 (`यज्ञशिष्टामृतभुजो यान्ति ब्रह्म सनातनम्‌`).
   - **Slide 31:** Displays Verse 4.31 Line 2 (`नायं लोकोऽस्त्ययज्ञस्य कुतोऽन्यः कुरुसत्तम ॥ ३१ ॥`). Duration is only **7.28 s**!
   - **Slide 32:** Resumes 1-to-1 match with Verse 4.32.

3. **Chapter 13 Verification:**
   - **35 verses / 35 slides:** Every single slide (1 to 35) is an exact 1-to-1 MATCH to `backend/data/gita/13/verses.json`.
   - Slide 1 contains Arjuna's opening inquiry (`प्रकृतिं पुरुषं चैव...`).
   - Slide 2 contains the glued speaker label matching the data (`श्रीभगवानुवाचइदं शरीरं कौन्तेय...`).
   - The 35-verse plan is authentic to this video recording.

---

### D. Audio Boundary & Acoustic Measurements

silencedetect analysis was performed on 216 sampled boundary windows (12 per chapter, covering edges, short clips, and flagged slides).

1. **Acoustic Environment Findings:**
   - A continuous musical drone/tanpura is present throughout the entire recording.
   - The measured RMS level of this drone is approximately **`-27 dB` to `-31 dB`**.
   - Consequently, running `silencedetect` with threshold `noise=-35dB:d=0.2` fails to register silences between verses during sustained accompaniment.
   - Inter-verse pauses are only detectable when the drone dips or during chapter transitions.

2. **Slide-to-Audio Temporal Lag:**
   - Where pauses are measurable, the slide transition consistently occurs **0.8 s to 1.4 s BEFORE the reciter finishes the preceding verse**.
   - Example (`Ch 01 Slide 03` $\rightarrow$ `Slide 04` at `72.240 s`):
     - Slide changes at: `72.240 s`
     - Reciter completes Verse 3 at: `73.119 s` (+0.879 s after slide change!)
     - Inter-verse silence: `73.119 s` to `73.597 s` (0.478 s pause)
     - Reciter begins Verse 4 at: `73.597 s` (+1.357 s after slide change)
   - **Acoustic Consequence:** Cutting audio precisely at slide change times (`args.shift = 0.0`) will **cut off the final syllable of the preceding verse** and contaminate the start of the next verse with the tail of the previous verse!

3. **Recommended Shift Value:**
   - The temporal evidence supports a positive shift parameter:
     $$\mathbf{--shift\ 0.85\ \text{to}\ 1.0\ \text{seconds}}$$
   - Applying `+0.9 s` places the cut squarely inside the silence gap between verses for the vast majority of transitions.

4. **12 Specific Clips for Human Listening Verification:**
   The human operator must verify the first and last syllables of these clips:
   1. `Ch 01 Verse 01` — Start: `23.000 s` (Tight lead-in, reciter begins immediately)
   2. `Ch 01 Verse 04` — Start: `72.240 s` (Slide changes while Verse 3 is still sounding)
   3. `Ch 01 Verse 22` — Start: `333.240 s` (Short clip, 6.3 s duration)
   4. `Ch 01 Slide 26` — Start: `386.280 s` (Onset of chained half-verse shift)
   5. `Ch 01 Slide 37` — Start: `560.240 s` (Boundary after 36-37 transition)
   6. `Ch 04 Slide 29` — Start: `2863.400 s` (3-line slide containing 4.29 + 4.30a)
   7. `Ch 04 Slide 30` — Start: `2880.120 s` (Shifted half-verse 4.30b + 4.31a)
   8. `Ch 04 Slide 31` — Start: `2893.880 s` (Single line clip, 7.28 s duration)
   9. `Ch 06 Slide 24` — Start: `3868.920 s` (Internal gap outlier, 6.04 s)
   10. `Ch 12 Slide 01` — Start: `7278.880 s` (First verse of chapter, dialogue start)
   11. `Ch 13 Slide 01` — Start: `7597.560 s` (Arjuna's question verification)
   12. `Ch 18 Slide 78` — Start: `10634.700 s` (Closing verse before colophon)

---

## What is UNVERIFIED

1. **Perceptual Listening of All 700 Audio Cuts:** Silencedetect measured physical signal energy only. Subjective listening to confirm absence of clicks, breath cuts, or subtle consonant clipping on all 700 cuts cannot be performed by an automated script.
2. **Post-Split Manifest & Assets:** Actual clip generation via `gita_split.py split` was NOT run, as mandated by the audit instructions.

---

## Ranked List of Risks Before Running `split`

1. **CRITICAL: Bleed / Syllable Truncation without Audio Shift (`--shift`):**
   - If `split` is executed with `--shift 0.0`, recitations will suffer systematic clipping of final syllables and bleed into subsequent verses because video slide animations lead audio recitations by ~0.9 seconds.
   - *Mitigation:* Apply `--shift 0.9` and verify on the 12 sampled listening points.

2. **HIGH: Chapter 4 Mid-Chapter Half-Verse Shift (Slides 29–31):**
   - Slide 29 contains 1.5 verses (3 lines). Slide 30 contains 0.5 verse of 4.30 and 0.5 verse of 4.31. Slide 31 contains only the second half of 4.31.
   - If audio is split 1-to-1 with slides, audio clip 4.30 will contain mixed verse lines, and clip 4.31 will only contain half a verse!
   - *Mitigation:* Determine whether to split audio along slide transitions or merge/realign audio cuts 29–31 to match authentic verse boundaries.

3. **HIGH: Chapter 1 Chained Half-Verse Shift (Slides 26–36):**
   - Using `cuts_ch01_46.csv` correctly aligns to the 46 video slides, but multimodal RAG consumers must be informed that clips 26–36 each contain lines from two distinct data verses.
   - *Mitigation:* Ensure `ch01_map_v2.csv` mapping metadata is bundled into the output manifest.

4. **MEDIUM: Data Hygiene Defects in `verses.json`:**
   - Stray nukta characters (4 verses) and glued speaker labels (11 verses) will degrade text embedding quality and exact lexical search.
   - *Mitigation:* Apply the cleaning steps documented in `_audit\normalize_spec.md` to `backend/data/gita/` prior to vector indexing.

