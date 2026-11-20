# VYOM retrieval benchmark

How well does each retrieval setup find the right Bhagavad Gita verses? Six configurations were each scored against two hand-judged gold sets. Everything below is local retrieval only: no LLM calls, CPU only. The results were re-run on 2026-11-19 after the Qdrant re-index.

## Results

20 non-routed questions; the 4 questions that name a verse go to the regex router and are excluded. Higher is better.

| Configuration | Strict hit@5 | Strict recall@5 | Strict MRR@10 | Lenient hit@5 | Lenient recall@5 | Lenient MRR@10 | Median latency |
|---|---|---|---|---|---|---|---|
| **dense bge-m3** (serving today) | 0.85 | 0.58 | 0.71 | 0.90 | 0.68 | 0.82 | 72 ms |
| **dense bge-base** | **0.85** | **0.60** | **0.82** | **0.90** | **0.70** | 0.83 | **33 ms** |
| hybrid bge-m3 | 0.70 | 0.43 | 0.70 | 0.90 | 0.59 | 0.84 | 70 ms |
| hybrid bge-m3 `--stopwords` | 0.80 | 0.53 | 0.78 | 0.90 | 0.64 | 0.82 | 67 ms |
| hybrid bge-m3 `--expand-always` | 0.70 | 0.43 | 0.70 | 0.90 | 0.60 | **0.85** | 78 ms |
| hybrid bge-m3 `--expand-always --stopwords` | 0.80 | 0.54 | 0.73 | 0.90 | 0.67 | 0.80 | 73 ms |

- **hit@5:** share of questions with at least one gold verse in the top 5.
- **recall@5:** gold verses found in the top 5, divided by min(number of gold verses, 5).
- **MRR@10:** 1 / rank of the first gold verse within the top 10.
- **Latency:** median over the 24 eval questions, measured in-process after one warm-up query. It covers query embedding, Qdrant search, and BM25 + RRF fusion for hybrid; no LLM. Run-to-run spread is about 10 %, and the p95 is within 15 ms of the median for every configuration.

### Paired comparison against dense bge-m3

Run with `compare_runs.py` (wins / losses / ties per question, and a paired bootstrap with 10,000 resamples, 95 % CI).

| Configuration | Gold | hit@5 W/L/T | Δ recall@5 [95 % CI] | Δ MRR@10 [95 % CI] |
|---|---|---|---|---|
| dense bge-base | strict | 0/0/20 | +0.02 [−0.05, +0.09] | **+0.11 [+0.01, +0.22]** |
| dense bge-base | lenient | 0/0/20 | +0.02 [−0.05, +0.08] | +0.01 [−0.12, +0.13] |
| hybrid | strict | 0/3/17 | **−0.15 [−0.28, −0.03]** | −0.01 [−0.12, +0.11] |
| hybrid `--stopwords` | strict | 1/2/17 | −0.05 [−0.18, +0.07] | +0.07 [−0.04, +0.19] |
| hybrid `--expand-always` | strict | 0/3/17 | **−0.15 [−0.27, −0.04]** | −0.01 [−0.13, +0.11] |
| hybrid `--expand-always --stopwords` | strict | 1/2/17 | −0.04 [−0.15, +0.06] | +0.02 [−0.09, +0.14] |
| all four hybrids | lenient | 0/0/20 each | −0.01 to −0.09, every CI includes 0 | −0.03 to +0.02, every CI includes 0 |

Bold marks the only intervals that exclude zero:
- bge-base ranks the first correct verse higher on strict gold.
- Plain hybrid and `--expand-always` without stopwords lose recall on strict gold.

## Method

1. **Questions.** 24 questions of four kinds:

   | Kind | Count | Example |
   |---|---|---|
   | conceptual | 10 | "How do I control a restless, wandering mind?" |
   | lookup | 6 | "Show me chapter 4 verse 7." |
   | word meaning | 4 | "What does the word sthitaprajna mean?" |
   | multi-verse | 4 | "How does dwelling on sense objects lead to ruin?" |

   Four lookups name a verse and are answered by the regex router, so the scores cover the other 20.
2. **Blind pooling.** For each of the 20 questions, the top 5 verses from all six configurations were pooled, together with the earlier v1 gold verses (21 of which no system retrieved). That gives **225 question–verse pairs**.
   - The pairs were written to a blind judging sheet (`retrieval/eval/blind_sheet.txt`) showing only the question and the verse's English text, in seeded-shuffle order, with no system names.
   - The mapping back to systems is kept separately in `pool_key.json`.
3. **Judging.** Each pooled verse was marked `[x]` (answers the question), `[~]` (on topic but does not answer) or blank (not relevant).
   - The first pass was LLM-assisted (`marks_pass1.txt`), then reviewed by hand and applied with `apply_marks.py` and `apply_judgments.py`. The LLM assistance is as reported by the project owner; the repository does not record it.
4. **Two gold sets.**
   - **Strict** gold (`questions.v2.jsonl`) is `[x]` only: on average 3.3 verses per question.
   - **Lenient** gold (`questions.v2_lenient.jsonl`) is `[x]` + `[~]`: 5.3 verses per question.
   - Strict asks "did it find a verse that answers?"; lenient asks "did it stay on topic?"
5. **Configurations.**
   - **Dense:** the query is embedded with bge-m3 (1,024-dim, multilingual) or bge-base-en-v1.5 (768-dim, English). The top 50 chunks come from Qdrant and are merged by verse.
   - **Hybrid:** dense bge-m3 plus BM25 over the same chunks (diacritics folded, hyphenated compounds also indexed joined), fused with reciprocal rank fusion (k = 60).
   - **`--stopwords`** drops English stopwords from the BM25 query.
   - **`--expand-always`** also matches corpus words that start with a query word (weight 0.5), even when the query word itself is in the vocabulary.
6. **Index.**
   - 1,569 chunks: 701 verse chunks (four English translations + IAST) and 868 Swami Sivananda commentary chunks, each up to about 1,200 characters with one sentence of overlap.
   - Re-indexed on 2026-11-19 after six Sanskrit typo fixes. The embedded text contains no Devanagari, so the vectors were bit-identical and all 12 re-runs matched the October results exactly.

Reproduce from `backend/`:

```powershell
..\venv\python.exe retrieval\eval\run_eval.py --mode dense --models bge-m3 bge-base --questions retrieval\eval\questions.v2.jsonl
```
```powershell
..\venv\python.exe retrieval\eval\run_eval.py --mode hybrid --models bge-m3 --expand-always --stopwords --questions retrieval\eval\questions.v2_lenient.jsonl
```
```powershell
..\venv\python.exe retrieval\eval\compare_runs.py --baseline retrieval\eval\results\bge-m3_dense_questions.v2.json retrieval\eval\results\bge-base_dense_questions.v2.json
```

## The sthitaprajna finding (why `--expand-always` exists)

The verses that define *sthitaprajna* ("one of steady wisdom") are 2.54 and 2.55. They use inflected forms: *sthita-prajñasya* (genitive) and *sthita-prajñas* (nominative), which BM25 tokenizes as `sthitaprajnasya` and `sthitaprajnas`.

- The query word `sthitaprajna` never matches those tokens exactly.
- The original BM25 expansion only fires for query words *missing* from the vocabulary. `sthitaprajna` is *present*, because Sivananda's commentary on 16.6 and 18.10 uses the bare form. So no expansion happened, and BM25 returned only those two commentary chunks.
- `--expand-always` adds prefix matches even for known words. With it, BM25 alone ranks 2.55 and 2.54 at positions 4 and 5.
- **But the fix doesn't survive fusion.** After RRF with the dense list, 2.55 and 2.54 land at fused ranks 6 and 8, just outside the top 5. The bare one-word query still misses in every configuration (table below).

## Known-hard queries: Sanskrit terms

Five queries built around a Sanskrit term. "Defining verses" are taken from the data: the verses whose IAST contains the term, after folding diacritics and hyphens. This dataset writes ś as "sh" and svadharma as both "sva-" and "swa-", so both spellings count.

Each cell shows the defining verses found in the top 5 (or ✗ if none).

| Query (defining verses) | dense bge-m3 | dense bge-base | hybrid | hybrid sw | hybrid ea | hybrid ea+sw |
|---|---|---|---|---|---|---|
| "sthitaprajna" (2.54, 2.55) | ✗ | ✗ (2.72, end of the passage) | ✗ | ✗ | ✗ | ✗ |
| "What are the marks of a sthitaprajna?" | ✗ | **2.54** (rank 1) | 2.54 | 2.54 | 2.54 | 2.54 |
| "svadharma" (2.31, 2.33, 3.35, 18.47) | 18.47 | ✗ | 18.47 | 18.47 | 18.47, 2.33 | 18.47, 2.33 |
| "What does the Gita say about sattva, rajas and tamas?" (14.5) | ✗ | 14.5 | 14.5 | ✗ | 14.5 | 14.5 |
| "sharanagati" (18.66) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Queries with a defining hit** | **1 / 5** | **2 / 5** | **3 / 5** | **2 / 5** | **3 / 5** | **3 / 5** |

What this shows:
- **Bare Sanskrit terms are the weak spot for every configuration.** "sharanagati" (a later devotional term for surrender, whose source is *mām ekaṁ śharaṇaṁ vraja*, 18.66) is never found.
- **Dense bge-m3 is weakest on these terms (1 of 5).** BM25 helps it most where the term appears in the IAST: svadharma with `--expand-always`, and the gunas question.
- **bge-base does better on natural-language Sanskrit questions** (the sthitaprajna and gunas questions) but misses bare "svadharma".
- **Possible next steps (not built):** query-side expansion of known Sanskrit terms to their defining verses, or adding Devanagari to the embedded text so bge-m3's multilingual vocabulary can match it.

## Serving recommendation

**Decision (2026-11-19):**
- Serving uses **dense bge-base** by default (`VYOM_EMBED_MODEL`, default `bge-base`).
- Queries that contain **Devanagari** are routed to **dense bge-m3** (`VYOM_SCRIPT_ROUTING`, on by default), because bge-base is English-only (see the Hindi check below).
- Hybrid is not used.

The comparison behind the decision:

| | dense bge-m3 (today) | dense bge-base | best hybrid (`--expand-always --stopwords`) |
|---|---|---|---|
| Strict hit@5 / recall@5 / MRR@10 | 0.85 / 0.58 / 0.71 | 0.85 / 0.60 / **0.82** | 0.80 / 0.54 / 0.73 |
| Lenient hit@5 / recall@5 / MRR@10 | 0.90 / 0.68 / 0.82 | 0.90 / **0.70** / 0.83 | 0.90 / 0.67 / 0.80 |
| Known-hard Sanskrit queries | 1 / 5 | 2 / 5 | 3 / 5 |
| Retrieval latency, median (CPU) | 72 ms | **33 ms** | 73 ms |
| Model load at startup (CPU) | 11–17 s | 8–14 s | 11 s + BM25 build |

Why bge-base:
- **Accuracy:** it ties or beats bge-m3 on every metric of both gold sets. Its first correct verse ranks higher on strict gold (MRR +0.11, 95 % CI [+0.01, +0.22]), the only statistically clear difference in the table.
- **Speed:** retrieval is about twice as fast (33 vs 72 ms), with a smaller model and smaller vectors.
- **Sanskrit terms:** it does better than bge-m3 (2 vs 1 of 5).

Why not hybrid:
- No hybrid configuration beats dense bge-m3 on hit@5 for either gold set.
- Plain hybrid and `--expand-always` lose recall on strict gold (−0.15, CI excludes 0).
- The best hybrid (`--expand-always --stopwords`) is roughly level with dense bge-m3 and does best on Sanskrit terms (3 of 5). But it doesn't beat bge-base on the gold sets, and it adds a BM25 index to build and keep in memory.

Caveats:
- **Small sample.** With n = 20, most differences fall inside their confidence intervals; the MRR gain is the only clear one.
- **English-only model.** bge-base-en-v1.5 is much worse on Devanagari queries (see below). Script routing sends those to bge-m3; Hinglish written in Latin script stays on bge-base.
- **Multi-query path not evaluated.** Serving runs `multi=true`: it decomposes questions and retrieves up to 5 verses per sub-question. The benchmark scores single-query retrieval only.
- **Cost of script routing:** both models stay loaded. Process working set after startup is 1,297 MB vs 990 MB with bge-base alone (+307 MB, read through the Windows API). Startup takes about 10 s longer for the extra model. Set `VYOM_SCRIPT_ROUTING=0` to load bge-base only.

## Hindi and Hinglish check

Run locally with `backend/_scratch/hindi_check.py`; top 5 verses. Bold verses are on topic.

| Query | dense bge-m3 | dense bge-base |
|---|---|---|
| "आत्मा अमर है" (the self is immortal) | **2.12, 2.20**, 9.31, 14.27, **2.30** | 17.23, 11.37, 11.11, 18.8, 10.12 |
| "मन को कैसे नियंत्रित करें?" (how to control the mind) | 17.14, 18.51, **6.26**, 6.36, 5.28 | 17.25, 13.13, 17.23, 18.55, 17.26 |
| "karma yoga kya hai" (Hinglish) | 13.25, 2.40, **3.3**, 2.50, 5.26 | 3.38, 5.26, 5.6, 5.1, 3.25 (nearby topics) |
| "man ko shant kaise karein" (Hinglish) | 5.3, 9.16, 1.5, 18.1, 3.37 | 18.43, 3.35, 11.17, 18.69, 11.49 |

What this shows:
- bge-base fails on Devanagari, so Devanagari queries are routed to bge-m3.
- Romanized Hinglish is weak for both models.
- The Devanagari terms in the concept router (next section) help either way. With routing off, "आत्मा अमर है" on bge-base still brings in 2.12–2.24 through the *atman* entry.

## Hand-curated concept router (not part of the retrieval numbers)

> **Hand-curated, not learned.** The figures above measure the retrievers alone. This section measures a hand-written keyword map on top of them. Several of its verses are also gold answers in the eval set, so it must never be counted in the retrieval benchmark.

**How it works.**
- `backend/retrieval/concepts.py` holds 16 core concepts: sthitaprajna, sharanagati, svadharma, nishkama karma, gunas, karma yoga, bhakti, jnana yoga, atman, paramatma, dhyana, yajna, maya, Om Tat Sat, samatva and moksha. Each maps to 4–6 verses chosen by the owner and checked against the translations.
- **Matching:** the query is folded so spelling variants meet: diacritics dropped, sh→s, w→v, gy/gn→jn, doubled vowels collapsed. Patterns allow an optional hyphen or space inside compounds, plus inflected endings.
  - "Sthithaprajna", "sthita-prajñasya" and "stithpragya" all match.
  - Devanagari terms match only when not glued to a preceding Devanagari letter, so परमात्मा doesn't trigger *atman*. "Mahatma" doesn't either.
  - Plain English questions trigger nothing.
- **Wiring:** `topic_boost.boost_verses` adds the concept verses after the existing contested-topic lists, just below the best search score for that sub-question. With 2 or more sub-questions, each concept contributes at most 3 verses (`MULTI_SUBQ_CONCEPT_CAP`); the contested-topic lists are never cut.

**The 5 hard queries through the serving retrieval path** (`retrieve_multi`, dense bge-base, one sub-question, up to 12 verses). Each cell shows the defining verses that reach the LLM context, with their position in that list.

| Query | Defining verses | Before | After |
|---|---|---|---|
| "sthitaprajna" | 2.54, 2.55 | none | 2.55 (#2), 2.54 (#4) |
| "What are the marks of a sthitaprajna?" | 2.54, 2.55 | 2.54 (#1) | 2.54 (#1), 2.55 (#2) |
| "svadharma" | 2.31, 2.33, 3.35, 18.47 | none | 3.35 (#2), 18.47 (#3), 2.31 (#5), 2.33 (#6) |
| "What does the Gita say about sattva, rajas and tamas?" | 14.5 | 14.5 (#2) | 14.5 (#2) |
| "sharanagati" | 18.66 | 18.66 (#2), from the existing *surrender* topic boost | 18.66 (#2) |

**Token check**, estimated offline with no LLM call, calibrated on a real Groq measurement (4.40 characters per token). The query was "What is sthitaprajna; what is svadharma; how do I control anger": 3 sub-questions, 2 concepts.

| Setup | Prompt tokens | What reaches the context |
|---|---|---|
| Before (no concept router) | ~2,556 | 12 verses, no defining verse for either concept |
| After, with the 3-per-concept cap | ~2,587 (+1 %) | 3.35, 18.47, 18.48, 2.55, and 6.26 / 17.6 for the anger sub-question |
| After, without the cap | ~2,573 | 2.31 and 2.33 push out 6.26 and 17.6 from the anger sub-question |

The overall 12-verse limit already caps the prompt size. The per-concept cap doesn't save tokens; what it does is keep room for the other sub-questions.
