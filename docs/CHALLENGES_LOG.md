# VYOM challenges log

Append only. One entry per non-trivial problem: Problem / Root cause / Fix (files) / Result.
Numbers come from real runs unless marked UNVERIFIED.

---

## 2026-11-19 · Phase 0 · Every rule sent to the LLM twice

**Problem.** A multi question with 3 sub-questions sent 4,972 prompt tokens to Groq (measured, `usage.prompt_tokens`). On the free tier (8K tokens/minute) that allows about one question per minute.

**Root cause.** `retrieval/prompt_v2.py`: every rule from `SYSTEM_PROMPT_V2` was repeated as an "Instructions:" block at the end of the user message (5,307 chars, about 1,000–1,300 tokens). The user message also carried Devanagari Sanskrit and IAST for every verse (about 900 tokens for 12 verses), which nothing downstream used.

**Fix.** Phase 1, below.

---

## 2026-11-19 · Phase 0 · 429s caused 12–16 s hangs, then 60 s of failover

**Problem.** On a Groq 429, a request hung for 12–16 s before failing over.

**Root cause (hypothesis, not reproduced).** `llm/client.py` built `Groq(api_key, timeout)` with no `max_retries`, so the SDK's default of 2 retries with backoff ran before our code saw the 429. Our handler then benched Groq for a fixed 60 s, whatever the real `retry-after` was.

**Fix.** Phase 1, below.

---

## 2026-11-19 · Phase 0 · Eval results older than the code they describe

**Problem.** The files in `backend/retrieval/eval/results/` date from 23–24 Oct. Verse-reference parsing (`parse_verse_refs`) changed on 11 Nov, and 6 Sanskrit typos were fixed without re-indexing.

**Root cause.** The eval was not re-run after those changes (HANDOFF "Next steps" #0).

**Fix.** Open. Decide in Phase 3/4 whether to re-run before publishing benchmark numbers.

---

## 2026-11-19 · Phase 1 · Prompt diet: one copy of the rules, no Sanskrit/IAST in the LLM context

**Problem.** See the first Phase 0 entry.

**Root cause.** Same.

**Fix.**
- `retrieval/prompt_v2.py`: removed the trailing "Instructions:" block. A script checked that all 59 of its sentences match a rule in `SYSTEM_PROMPT_V2`; 15 differ only in wording.
- The order is now: static system prompt, then verses, then the question and sub-questions last.
- Dropped the `Sanskrit:` and `Transliteration:` lines from the LLM context. The verifier and post-processing never read Sanskrit or IAST, and the cards render both from `sources`, which still carry them.
- Tests: 3 tests changed from "rules in both copies" to "rules in the system prompt, no Instructions block in the user message".

**Result.** Measured with Groq `usage`, in-process `/api/ask` with `multi=true`:

| Question | Prompt tokens before | Prompt tokens after |
|---|---|---|
| "What is nishkama karma; how do I control anger; what happens to the soul after death" (12 verses) | 4,972 | 2,665 (−46 %) |
| "How to master an agitated mind?" | ~3,000–4,000 (estimate) | 2,044 |
| "Explain BG 2.47" | ~2,700–3,700 (estimate) | 1,985 |

Groq returned `prompt_tokens_details: null` on every call, so it reported no cached tokens for `openai/gpt-oss-120b` on this account.

---

## 2026-11-19 · Phase 1 · 429 handling and response caching

**Problem.** See the second Phase 0 entry. Repeated demo questions also cost full tokens every time.

**Fix.**
- `llm/client.py`:
  - `Groq(..., max_retries=0)`.
  - On a 429, read `retry-after`. If it is ≤ 5 s, sleep and retry once. Otherwise put the provider on a cooldown of `retry-after` seconds (10 s if the header is missing) and fail over at once.
  - `_call_provider()` was extracted from the loop.
  - New `get_last_provider()`. Cached tokens are now logged.
- `llm/cache.py` (new): two thread-safe LRU caches, size from `VYOM_CACHE_SIZE` (default 128; 0 turns them off).
- `api/main.py`: `ask()` now wraps `_ask_uncached()`.
  - Cache key: normalized question, `multi`, `top_k`, primary model and reasoning effort.
  - Logs `CACHE_HIT` / `CACHE_STORE` / `CACHE_SKIP`. New headers `X-VYOM-Cache` and `X-LLM-Provider`.
  - Answers from a fallback provider and errors are not cached.
- `retrieval/multi.py`: the LLM splitter result now goes into a bounded LRU (normalized key + model), replacing the unbounded exact-string dict. The hand-seeded decompositions are unchanged.
- Tests: `tests/test_rate_limit_and_cache.py` (12 new); `conftest.py` clears both caches around every test.

**Result.**
- Tests: 228 → 240 passed.
- 3 different questions back to back: 2.03 s, 1.18 s, 1.68 s, no 429. Groq total was 7,356 tokens, just under the 8K/minute limit, so a 4th new question inside the same minute would probably still get a 429 (UNVERIFIED).
- A repeated question with different case and punctuation: cache HIT, 0.00 s, 0 Groq tokens.
- The 429 path is covered by unit tests only; no live 429 was triggered.
- Completion tokens before → after: 503 → 362 on the 3-sub-question query. After the change, the other two questions used 153 and 147 (cap 1800).

---

## 2026-11-19 · Phase 1 follow-up · Answers shrank after the prompt dedup

**Problem.** After the duplicated instructions block was removed, "How to master an agitated mind?" got a 62-word answer (target about 250). The 3-sub-question answer fell from 215 to 163 words.

**Root cause.** The dedup also removed the only length cue at the end of the prompt. The "about 250 words" rule now sat only at the top of a ~2K-token system prompt, and the model followed it weakly.

**Fix.** `retrieval/prompt_v2.py`: one `LENGTH_REMINDER` line after the sub-questions: "Answer in about 200-300 words total, one section per sub-question." Also in this follow-up:
- The Sanskrit rule now reads "…only if they appear verbatim in the translations shown", matching what the LLM actually sees.
- Groq `max_tokens` lowered from 1800 to 1000, since observed completions were 147–503.

**Result.** 1 real request, "How to master an agitated mind?":
- Answer: 62 → 124 words. Better, but still under the 200–300 target.
- Prompt tokens: 2,044 → 2,060 (+16).
- Completion: 298 tokens, 118 of them reasoning.
- Latency: 6.71 s for this one call (earlier calls were 1–2 s).

---

## 2026-11-19 · Phase 2 · The Gemini "404" is now a 403: no free tier on this project

**Problem.** Gemini was meant to be the second provider, but it never answered.

**Root cause.** Checked with the REST API, key sent in a header:
- Listing models works (50 models support generateContent).
- `generateContent` returns **403 PERMISSION_DENIED, "The Gemini API free tier is not available for this project"** for gemini-2.5-flash, gemini-2.5-flash-lite and gemini-1.5-flash.
- The earlier 404 most likely came from the retired `gemini-1.5-flash` code default; that is UNVERIFIED, because the 403 now comes back first.
- This is an account or project limit. No model name or SDK change fixes it.

**Fix.**
- `llm/client.py` and `.env.example`: default model changed from `gemini-1.5-flash` to `gemini-2.5-flash`.
- No SDK migration yet: `google-genai` is not installed, and the migration can't be tested until a key works.
- The client already marks a provider dead on 403, so after one failure (about 1.5 s) Gemini costs nothing.

**Result.** `_scratch/failover_check.py`: gemini alone → FAIL 403 in 1.47 s. To make Gemini work: create a key in Google AI Studio under a project with free-tier access, or enable billing.

---

## 2026-11-19 · Phase 2 · Ollama fallback missing, and it would have cut the prompt

**Problem.** Ollama is the last fallback, but it isn't installed: nothing on PATH or in Program Files, no `~/.ollama`, and nothing listening on port 11434. Separately, `_call_ollama` sent no `num_ctx`, so a ~2–3K-token v2 prompt could be silently truncated to Ollama's default context window. It also used the 30 s cloud timeout, which is tight for a cold model load into VRAM.

**Fix.** `llm/client.py`: the Ollama payload sets `options.num_ctx` (default 8192, env `OLLAMA_NUM_CTX`), and the timeout is 120 s (env `OLLAMA_TIMEOUT`). Tests: `tests/test_failover.py` (4 new), covering:
- the payload settings;
- Gemini 403 marked dead, then Ollama answers;
- the quote verifier removing a fabricated quote when Gemini or Ollama answered.

**Result.**
- Tests: 240 → 244.
- Live chain with Groq off: `/api/ask` returns a clean HTTP 503 in 5.27 s (Gemini 403, then Ollama ConnectError after about 4 s), with no long hang.
- With Groq on, the full chain answers from Groq in 1.5 s.
- Ollama answers not tested live (not installed).

---

## 2026-11-19 · Length cue, second try, and the 6.71 s outlier

**Problem.** Even with the end-of-prompt reminder, "How to master an agitated mind?" got 124 words (target 200–300). That request also took 6.71 s, against about 1–2 s for the others.

**Fix tried.** `retrieval/prompt_v2.py`: `LENGTH_REMINDER` changed to "Write 180-250 words in total, one section per sub-question."

**Result.**
- 1 real request: 113 words, 272 completion tokens (120 reasoning), 1.66 s end to end. Still short. Stopped here; the owner will judge it in the browser.
- The latency breakdown is now logged:
  - Groq's own timing: queue 0.16 s, prompt 0.10 s, completion 0.57 s, total 0.67 s.
  - The client-side Groq call took 1.14 s, so about 0.47 s went to connection and network.
  - Server timing: retrieval 0.50 s on CPU, generation 1.15 s, verification 0.004 s.
- The 6.71 s outlier had about the same output (298 completion tokens), so output length doesn't explain it. Groq's own timing wasn't captured on that call, so it was Groq-side queueing or network: UNVERIFIED which.

---

## 2026-11-19 · Gemini removed from the default chain

**Problem.** Re-checked Gemini: still 403 "free tier is not available for this project" for every model.

**Fix.**
- `llm/client.py`: `DEFAULT_LLM_PROVIDERS = "groq,ollama"`. Gemini can be re-enabled with `LLM_PROVIDERS=groq,gemini,ollama`.
- `tests/test_generation_api.py`: the Gemini success test now sets `LLM_PROVIDERS=gemini` explicitly.
- New test `test_gemini_is_not_in_the_default_chain`.
- CLAUDE.md updated.

**Result.**
- Tests: 244 → 245.
- A request no longer spends about 0.8–1.5 s on a doomed Gemini call when Groq is unavailable.

---

## 2026-11-19 · bge-m3 runs on CPU at serve time

**Finding.** The venv's torch is `2.14.1+cpu`, so `torch.cuda.is_available()` is False, and `SentenceTransformer` (no device argument) loads bge-m3 on CPU in float32. Retrieval takes about 0.5 s per query.

**Consequence.** bge-m3 uses no VRAM, so a local Ollama model would get the whole RTX 4060 (8 GB, about 160–190 MiB in use at idle). No change made.

---

## 2026-11-19 · groq2 tier, one reused Groq client, Gemini back over REST

**Problem.**
- Groq is the only working provider, and its 8K tokens/minute limit applies per model.
- Every `_call_groq` built a new Groq client, so every call paid a new TLS handshake (client side 1.14 s vs Groq's own 0.67 s).
- With the owner's new key, Gemini returned **404 "no longer available to new users"** for gemini-2.5-flash and -lite (no longer 403). Google pointed to newer models.

**Fix (`llm/client.py`).**
- New provider `groq2` = `GROQ_FALLBACK_MODEL` (default `openai/gpt-oss-20b`), sharing the same reasoning settings.
- Default chain `groq,groq2,gemini,ollama`.
- `_groq_client()` caches one `Groq(max_retries=0)` per key; the 429 logic is unchanged.
- `_call_gemini` rewritten as plain REST (httpx, key in an `x-goog-api-key` header), replacing the deprecated `google.generativeai` SDK, which is no longer imported. It records usage and maps `MAX_TOKENS` to `length`.
- Default `GEMINI_MODEL` changed to `gemini-3.5-flash-lite`, the only free model that answered (gemini-3.8-flash returned 503 "high demand"). `.env.example` updated too. `backend/.env` still says gemini-2.5-flash and needs the owner's edit.

**Tests.** 245 → 249:
- groq 429 falls to groq2 with the 20b model;
- the client is created once and reused;
- a Gemini REST 404 marks Gemini dead;
- the verifier test now also covers groq2;
- the Gemini REST request shape.

**Result (live).**
- `failover_check.py`: groq 0.89 s, groq2 0.40 s, gemini 3.4–9.5 s, ollama ConnectError in 4.1 s.
- groq2 forced, agitated-mind chip query: 91 words, 3× (BG 6.35), no verifier removals, 1.15 s.
- Gemini forced (Groq and groq2 off), `/api/ask`: HTTP 200 in 4.91 s, 96 words, (BG 6.35) cited, no removals.
- Both fallback models added a "### 1." heading to a single-question answer; the system prompt says not to.

---

## 2026-11-19 · Phase 3 · Re-index after the Sanskrit fixes, and a hidden pipeline trap

**Problem.** The 6 Sanskrit typo fixes of 2026-11-11 (1.26, 1.34, 4.29, 4.31, 9.25, 10.29) were in `verses.jsonl` but not in Qdrant. Its payloads still had the old Sanskrit (0/6 matched).

**Root cause.**
- `chunks.jsonl` (20 Oct) predates the fix.
- The normal rebuild path, `ingestion/chunk.py` `main()`, re-cleans the raw dataset through `clean.py` and **overwrites `verses.jsonl`**. Running it would have silently undone the fixes.
- The fixes were made by hand in `verses.jsonl` only, not in the cleaning pipeline.

**Fix.**
- Backed up (copies): `backend/qdrant_data.bak1`, `data/processed/chunks.jsonl.bak1`, `data/processed/embeddings.bak1/`.
- `_scratch/rebuild_chunks.py` reuses `chunk.build_chunks()` but feeds it the canonical `verses.jsonl` and writes only `chunks.jsonl`.
- Diff against the old chunks: 1,569 chunks, ids and order unchanged, 0 `embed_text` changes, `sanskrit` payload changed only in the 6 verse chunks. The embedded text uses English translations and IAST, never Devanagari.
- `verses.jsonl` SHA-256 is unchanged.
- Then `embed.py` and `build_index.py` for both models, on CPU.

**Result.**

| Model | Embed time | Index time | Points | Fixed verses with correct Sanskrit |
|---|---|---|---|---|
| bge-m3 | 688 s | 7 s | 1,569 | 0/6 → 6/6 |
| bge-base | 275 s | 6 s | 1,569 | 0/6 → 6/6 |

- New vectors are bit-identical to the old ones (max |diff| 0), so the existing retrieval eval results are not invalidated by the re-index itself.
- Local retrieval (no LLM):
  - "How to master an agitated mind?" → bge-m3 6.26, 6.15, 6.25, 5.28, 6.35.
  - "sthitaprajna" → bge-m3 18.10, 13.8, 18.37, 3.27, 4.29; bge-base 18.10, 2.72, 4.6, 4.11, 17.6. bge-base finds 2.72, which ends the sthitaprajna passage; bge-m3 finds none of 2.54–2.72.
- Tests: **248 passed, 1 failed** (`test_chunk.py::test_chunking_deterministic`). The test rebuilds chunks from raw data via `clean.py`, which lacks the 6 fixes, and compares them with the saved `chunks.jsonl`, which has them.
- The failure is the pipeline trap above, now visible. Open; needs the owner's decision.

---

## 2026-11-19 · Sanskrit fixes moved into the pipeline (closes the Phase 3 test failure)

**Problem.** `test_chunk.py::test_chunking_deterministic` failed after the re-index. The raw pipeline (`clean.py` → `chunk.py`) produced the *unfixed* Sanskrit, because the 6 fixes existed only in `verses.jsonl`.

**Root cause.** The 2026-11-11 typo fixes were hand edits to a generated file. Any re-run of `chunk.py` would also have silently reverted them.

**Fix.**
- `ingestion/clean.py`: `SANSKRIT_CORRECTIONS` table, 7 entries (verse_id, old, new) for 1.26 (×2), 1.34, 4.29, 4.31, 9.25 and 10.29. Five remove a stray nukta, one is श्च→श्व, one adds a missing anusvara.
- `apply_sanskrit_corrections()` runs inside `load_clean()` and raises `ValueError` if a verse is unknown or `old` is not found exactly once.
- Backup: `clean.py.bak1`.
- `sanskrit-data` skill: hand-editing verse text is now forbidden; fixes go in the table.

**Result.**
- `_scratch/check_pipeline_repro.py` runs `chunk.py` `main()` into a temp folder: `verses.jsonl` and `chunks.jsonl` are byte-identical to `data/processed` (SHA-256 6b0068…, 48cbf3…). `verses.jsonl` SHA is unchanged.
- The `sanskrit-data` check equals its baseline (58 / 18 / 15 / 0 / 0 / 20).
- Tests: 249/249, then 266 with the new tests.

---

## 2026-11-19 · "### 1." heading on single-question answers

**Problem.** gpt-oss-20b (groq2) and Gemini open single-question answers with "### 1. <question>", against prompt rule 2.

**Fix.**
- `api/main.py`: `strip_single_section_heading()` is step 5e of `verify_and_clean_answer`, which takes a new `n_sub_questions` argument. The single-verse path passes 1; the multi path passes `len(sub_questions)`.
- It drops a numbered heading only when it is the only one and opens the answer, so it covers every provider.
- Applied by script from `main.py.bak5`. An earlier Edit-tool attempt triggered the formatter hook, which reformatted the whole file; that version was discarded.

**Result.** 17 new tests in `tests/test_heading_and_corrections.py`: heading variants, multi-section answers left alone, the API path for groq / groq2 / gemini / ollama, and corrections fail-loud cases. 266/266 pass.

---

## 2026-11-19 · Phase 4 · Eval re-run, benchmark, and where the sthitaprajna fix gets lost

**Problem.** The eval results predated the 2026-11-11 verse-ref parsing change and the re-index.

**Fix.**
- Backed up `retrieval/eval/results` to `results.bak1`.
- Re-ran all 6 configs × strict/lenient (12 runs, 222 s, local only).
- `_scratch/hard_queries_latency.py` covers 5 Sanskrit-term queries and CPU latency for each config.
- Wrote `docs/BENCHMARK.md`.

**Result.**
- All 12 runs are **identical** to October: same 4 routed questions, same top 10 for every question. The parsing change doesn't affect these 24 questions, and the vectors were bit-identical.
- Dense bge-base ties or beats dense bge-m3 everywhere. Strict MRR is +0.11 (95 % CI [+0.01, +0.22]), and median retrieval is 33 vs 72 ms.
- Plain hybrid and `--expand-always` lose strict recall (−0.15, CI excludes 0).
- **sthitaprajna, found in detail:**
  - The bare token `sthitaprajna` *is* in the BM25 vocabulary (Sivananda's commentary on 16.6 and 18.10), so the default expansion never fires.
  - `--expand-always` lifts 2.55 and 2.54 to BM25 ranks 4 and 5, but RRF fusion with the dense list pushes them to fused ranks 6 and 8.
  - The bare one-word query misses in all 6 configs.
- The dataset writes the same word inconsistently in IAST ("sva-dharmaṁ" in 2.33 vs "swa-dharma" in 3.35 and 18.47, and ś as "sh"), which limits exact-term BM25.
- The brief's "old baseline hit@5 0.67 (bge-m3) vs 0.75 (bge-base)" is not reproducible from any saved results file. v1 gold gives 0.85 / 0.85 non-routed for dense, and 0.70 / 0.75 for hybrid bge-m3 / bge-base. So it was left out of `BENCHMARK.md`.

---

## 2026-11-19 · Why hybrid retrieval didn't help (summary for the record)

- **Lexical noise.** BM25 runs over English translation chunks, where common words ("what", "does", "the") match everywhere. Plain hybrid lost strict recall@5 (−0.15, 95 % CI [−0.28, −0.03]). Dropping stopwords recovered most of it (−0.05, CI includes 0), but no hybrid beat dense on hit@5.
- **Fusion demotion.** Where BM25 does find a Sanskrit term's defining verses (sthitaprajna with `--expand-always`: 2.55 and 2.54 at BM25 ranks 4 and 5), reciprocal rank fusion with the dense list pushes them to ranks 6 and 8, out of the top 5.
- **Inconsistent IAST spellings in the dataset.** ś is written "sh", and svadharma appears as "sva-dharmaṁ" (2.33) and "swa-dharma" (3.35, 18.47). Exact-token BM25 can't connect these.
- **Baseline discrepancy dropped.** The "hit@5 0.67 vs 0.75" baseline quoted in the sprint brief can't be reproduced from any saved results file, so it isn't used anywhere.

---

## 2026-11-19 · Serving model: bge-base, but Hindi needs bge-m3

**Problem.** The benchmark favours dense bge-base (English questions), but bge-base-en-v1.5 is an English-only model.

**Check.** `_scratch/hindi_check.py`, local, top 5:

| Query | bge-m3 | bge-base |
|---|---|---|
| "आत्मा अमर है" | 2.12, 2.20, 9.31, 14.27, 2.30 (on topic) | 17.23, 11.37, 11.11, 18.8, 10.12 (none relevant) |
| "मन को कैसे नियंत्रित करें?" | includes 6.26 | chapters 17–18 only |
| "karma yoga kya hai" | 3.3 | 3.25, 5.1, 5.6 (adjacent) |
| "man ko shant kaise karein" | fails | fails |

bge-base is clearly worse on Devanagari.

**Fix.**
- `api/main.py`: the serving model comes from `VYOM_EMBED_MODEL` (`bge-base` | `bge-m3`, default `bge-base`; an unknown value logs a warning and uses the default).
- `/api/health` reports `embed_model`.
- Applied by script from `main.py.bak6`.
- Tests: `tests/test_embed_model.py` (5).

**Result.**
- Tests: 271/271.
- `_scratch/ask_retrieval_sanity.py` (real startup and retrieval, LLM stubbed):
  - bge-base: "restless mind" → 6.26, 6.34, 6.35 among the sources; "marks of a sthitaprajna" → 2.54 first.
  - bge-m3: "आत्मा अमर है" → 2.12, 2.20, 2.30.

---

## 2026-11-19 · Hand-curated concept router for Sanskrit terms

**Problem.** Bare Sanskrit terms ("sthitaprajna", "svadharma") never reached their defining verses with any retriever (Phase 4). The dense models don't know the terms, BM25 is defeated by inflection and inconsistent IAST, and fusion demotes what BM25 finds.

**Fix.**
- `retrieval/concepts.py` (new): 16 owner-approved concepts → verses.
  - Atman and paramatma are separate entries. Paramatma maps to 13.23, 15.17, 13.28, 6.7, all checked against the translations.
- **Matching:** normalized Latin text (diacritics dropped, sh→s, w→v, gy/gn→jn, doubled vowels collapsed), optional hyphen or space inside compounds, inflected endings. Devanagari terms can't be glued to a preceding Devanagari letter.
- **Wiring:** `topic_boost.boost_verses(..., concept_cap)` appends concept verses after the contested-topic lists. `multi.retrieve_multi` passes `MULTI_SUBQ_CONCEPT_CAP = 3` when there are 2+ sub-questions.
- **Integration choice:** this extends `topic_boost`, not the verse-ref regex router. The router forces verses in as "Requested by the user", which the prompt reads as "the user asked about this verse".
- Applied by script. Backups: `topic_boost.py.bak1`, `multi.py.bak3`.

**Result.**
- 55 new tests in `tests/test_concepts.py`: spelling variants, Devanagari, "Mahatma" / "paramatma" / परमात्मा don't trigger atman, 8 plain-English questions trigger nothing, the cap, and topic lists never cut.
- Serving path (bge-base), 5 hard queries:
  - bare "sthitaprajna": none → 2.55 (#2), 2.54 (#4);
  - "svadharma": none → 3.35, 18.47, 2.31, 2.33;
  - the other three were already found (sharanagati through the existing surrender boost).
- Tokens for a 3-sub-question, 2-concept query: ~2,556 → ~2,587 (+1 %). The 12-verse cap already bounds size; the per-concept cap keeps two anger verses that the uncapped version pushes out.

---

## 2026-11-19 · Devanagari queries routed to bge-m3

**Problem.** bge-base (now the default) is English-only and fails on Devanagari.

**Fix.**
- `retrieval/search.py`: `Searcher(model, client=None)`. A second Searcher can share the first one's local Qdrant client (local Qdrant allows one client per folder), and only the owner closes it.
- `api/main.py`:
  - when the default model isn't bge-m3, the lifespan also loads bge-m3 on the shared client;
  - `pick_searcher()` sends queries containing Devanagari to it (log `EMBED_ROUTE`);
  - `VYOM_SCRIPT_ROUTING=0` turns it off;
  - `/api/health` reports `devanagari_model`.
- Backups: `search.py.bak1`, `main.py.bak7`. Tests: 4 more in `tests/test_embed_model.py`.

**Result.**
- Live, LLM stubbed: "आत्मा अमर है" → 2.12, 2.13, 2.20, 2.22, 2.23, 2.24, 2.30. English queries are unchanged.
- Process working set after startup: 1,297 MB vs 990 MB (+307 MB). The sanity run took 27 s vs 17 s (extra model load).
- Even with routing off, the *atman* Devanagari concept trigger brings 2.12–2.24 into the bge-base results.

---

## 2026-11-19 · Formatter hook kept reformatting backend Python

**Problem.**
- The user-level PostToolUse hook (`~/.claude/hooks/format-on-edit.js`, ruff and eslint) reformatted whole backend files on every Edit/Write. That forced all backend patches through scripts, and it once rewrote all of `api/main.py`.
- A project `.claude/settings.json` can add hooks but can't narrow a user-level one, and the project had no settings file at all. So the "git is hard-blocked in `.claude/settings.json`" note in HANDOFF was not true.

**Fix.**
- The hook script (backup `format-on-edit.js.bak1`) gained an optional per-project scope: if the nearest `.claude/settings.json` above the edited file sets `env.FORMAT_ON_EDIT_ONLY`, only files under those folders are formatted. +24 lines, nothing else changed.
- New `D:\VYOM-AI\.claude\settings.json`: `{"env": {"FORMAT_ON_EDIT_ONLY": "frontend/"}}`.
- First attempt bug: Claude Code exports a project's `env` to the whole session. My first version also honoured the process env, which then scoped unrelated files under the home folder via `~/.claude/settings.json`. Fixed: only the settings file that declares the value counts.

**Result.** Hook fed real PostToolUse JSON:
- `backend/_scratch/hook_probe.py` → untouched;
- `frontend/hook_probe.py` → formatted;
- a file outside any scoped project → formatted as before.

---

## 2026-11-19 · Sprint cleanup: dependencies, gitignore, regeneration docs

**Problem.**
- `backend/pyproject.toml` declared `dependencies = []`, and there was no requirements file, so a fresh checkout couldn't be installed reproducibly.
- Large regenerable artefacts (239 MB of recitation clips, the 664 MB source video, embeddings, Qdrant storage) had no documented rebuild path.

**Fix.**
- `backend/requirements.txt`: exact pins from the working environment (Python 3.12.0), limited to the 12 third-party packages the backend code and tests import (found by an AST scan), plus `uvicorn` and CPU-only `torch` via the PyTorch CPU index.
- `pyproject.toml`: the same packages as lower bounds. It can't carry `--extra-index-url`, so exact pins stay in requirements.txt.
- `.gitignore`: clip audio, `lecture.mp4`, `frontend/public/audio/verses/`, Qdrant storage, embeddings, `*.npy`. Ignoring doesn't untrack files git already tracks; the owner checks that.
- README: "Rebuilding the index" (chunk → embed → index, with the byte-for-byte check) and "Regenerating audio clips" (yt-dlp, then `gita_split.py split` with the committed `cuts_final.csv`).
  - `split --dry-run` printed 700 verse-clip ffmpeg commands to the same paths `verse_clips.json` uses.
  - The yt-dlp step is unverified: yt-dlp isn't installed here.
- Deleted unused `frontend/src/assets/hero.png` and `frontend/public/audio/BG2.47.mp3` after a repo-wide grep found no references.

**Result.**
- 330/330 tests.
- Frontend build OK; lint exits 0.
- Requirements check: next entry.

---

## 2026-11-19 · Correction: audio clips are tracked in Git LFS on purpose

**Problem.** The cleanup entry above added the clip folders to `.gitignore`, but the 700 clips are tracked with Git LFS on purpose so the hosted app can serve them.

**Fix.**
- `.gitignore`: removed `backend/data/multimodal/source/assets/audio/` and `frontend/public/audio/verses/`. Still ignored: `lecture.mp4`, Qdrant storage, embeddings, `*.npy`.
- README: "Audio clips" now says `git lfs install` + `git lfs pull` after cloning. The yt-dlp + `gita_split.py split` steps moved to an optional "rebuild from the source recording" subsection. The recitation credit (Radha Gopinath Prabhu, Hare Krsna TV) is now also directly under the pitch.

**Findings (no git commands run).**
- `.gitattributes` LFS patterns: `*.mp3`, `*.wav`, `frontend/public/audio/**`, `backend/data/multimodal/**`.
- The last rule catches *every* file under `backend/data/multimodal`, about 137 MB of non-audio: 971 PNG, 120 .py, 27 CSV, 19 TXT, 13 JSON (including `verse_clips.json`, which `api/clips.py` reads, and `vyom_clips_v5.json`, which `prompt_v2.py` reads), plus logs and HTML.
- Clips are not duplicated. Backend `source/assets/audio/`: 700 verse clips (117 MB) + 18 chapter files (122 MB). `frontend/public/audio/verses/`: only `bg_02_47.mp3` (168 KB, byte-identical to the backend copy).
- **What's served in dev (tested):** with only Vite running, `/audio/verses/bg_02_47.mp3` returned 502 from the proxy, like a clip that isn't in `public/`. The `/audio` proxy wins over `public/`, so every clip comes from the backend's `/audio` route.
- In a production build the `public/` copy lands in `dist/audio/verses/`; which copy a host serves depends on its routing (unverified).

**Requirements check (completes the cleanup entry above).** A fresh venv (Python 3.12.0) installed `backend/requirements.txt` cleanly in 477 s. It got torch 2.14.1+cpu from the CPU index and sentence-transformers 6.1.0. The full suite there: **330 passed**. The throwaway venv was then deleted.

---

## 2026-11-19 · Debug PNGs and OCR models out of git

**Decision (owner).** The narrower LFS rule would have moved 971 debug-frame PNGs (194.6 MB) and two Tesseract models (12.9 MB) into plain git. They are now ignored instead.

**Checks.**
- A repo-wide grep shows no app or test code reads a PNG under `backend/data/multimodal`. `gita_split_slides.py` only *writes* verification PNGs.
- The traineddata files are needed only by the OCR audit scripts (`_audit/run_blind_ocr.py`, `_audit/test_ocr.py`, `_probe/lines/quick_ocr_ch1.py`, `--tessdata-dir _audit -l san+hin`).

**Fix.**
- `.gitignore` (backup `.gitignore.bak2`): `backend/data/multimodal/**/*.png` and `backend/data/multimodal/**/*.traineddata`.
- README: one line naming the models and where to get them.
- Local copies' SHA-256, for matching a re-download:
  - `san.traineddata` a3999589…271825
  - `hin.traineddata` 4c73ffc5…b91c
- Which tessdata variant (standard, fast or best) they came from wasn't recorded.

**Owner action.** These files are already tracked in LFS, and `.gitignore` doesn't untrack them; `git rm --cached` is needed (commands in the sprint report).

**Correction to the hashes just above** (their tails were swapped). The full SHA-256 values are:
- `san.traineddata`: a399958921c64e7d2319369ade1e74b4db2577744ac5bfeabd16663cf743b91c
- `hin.traineddata`: 4c73ffc59d497c186b19d1e90f5d721d678ea6b2e277b719bee4e2af12271825

---

## 2026-11-19 · Chat UX batch 1: no invented answers, Stop, verse lookup for all 701

**Problem.**
- When `/api/ask` failed with a 4xx, timed out or couldn't be reached, the chat showed a ready-made "offline" answer. That text included hand-written transliteration the quote verifier never saw.
- Verse chips and the "Exposition" link only worked for 11 verses.
- There was no way to stop a request.

**Root cause.**
- `services/api.ts` caught every error except 429/5xx and returned `generateOfflineGitaWisdom()`.
- `lookupVerse()` only knew the 11 hand-written entries in `data/gitaVerses.ts`.
- Those 11 entries pair their English text with author names that don't match the canonical translations in `verses.jsonl`. All 11 differ. 2.47's text, for example, is not Sivananda's.

**Fix (files).**
- `services/api.ts`:
  - typed `AskError` (aborted / busy / server / bad_request / timeout / network), with the caller's AbortSignal plus the 90 s timeout
  - reads the `X-VYOM-Cache` / `X-LLM-*` headers
  - 502/504 from the proxy count as "can't be reached"
  - the offline generator is removed
- `App.tsx` and `components/ChatPanel.tsx`:
  - a failed or stopped question becomes an in-conversation note (no answer text) with Retry
  - a Stop button while loading
  - the top banner is removed
- `data/verseStore.ts` (new): `normalizeVerseId` and `loadVerse` for all 701 verses. It reads `public/verses/chNN.json`, generated by the new `frontend/scripts/export_verses.py` from `verses.jsonl`, and the existing `public/translations/chNN.json`. Curated entries only add their theme and commentary note.
- `components/VerseDetailModal.tsx`: loading and error states with "Try again"; sections without data are hidden.
- Backups: `*.bak1` next to each edited file.

**Result.**
- `npm run build` and lint pass, and the backend tests pass (330).
- Checked in the browser with the backend stopped: the network error note, Retry replacing it, Stop (with a stubbed slow request), the modal for 13.35 and 5.10, the error state and Try again, the quote card from a chip, and 375px.
- Not yet checked with a live backend.
- The Sacred Book reader still shows the 11 curated Sanskrit/author pairs and the `shlokaDirectory` text: the 18 known mismatches, see `sanskrit-data`. Not changed.

---

## 2026-11-19 · Chat UX B1.5: Sacred Book on canonical text, speaker labels

**Problem.**
- The Sacred Book showed Sanskrit and IAST from `shlokaDirectory.json`, which has 18 real mismatches against `verses.jsonl`.
- For 10 verses it showed hand-written text from `gitaVerses.ts`. That text came with author credits that don't match the dataset, and with a "Commentary note" that had no known source.
- Speaker lines ("अर्जुन उवाच") were displayed three different ways.

**Root cause.**
- `verses.jsonl` stores speakers inconsistently. 60 verses have one:
  - in the Sanskrit, some are on their own line and some are joined to the verse (12.1, 12.2, 13.2, 14.1, 14.21, 14.22, 15.1, 17.1, 17.2, 18.73, 18.74)
  - in the IAST, always on their own line
- The reader only recognised "श्रीभगवानुवाच" on its own line.

**Fix (files).**
- `components/GitaBookReader.tsx`: text and translations now come from `data/verseStore.ts`, through a single chapter cache, with Loading and "Try again" states. `SHLOKA_DIRECTORY` is used only for order and audio.
- `data/gitaVerses.ts`: the 10 hand-written entries are removed (Sanskrit, IAST, translation, author, theme, commentary note). Only the `GitaVerse` type is left.
- `utils/speaker.ts` (new) splits the 5 real speakers off the start of the Sanskrit and IAST, for display only. Narrative "उवाच" (1.25, 2.10) is left in the verse. The speaker shows as a small label above the verse in the reader, verse modal, chat cards and quote card.
- `check_sanskrit.py`: new `[UI]` lines.
- `CLAUDE.md` and the `sanskrit-data` skill: generated files documented, and the old "80 mismatches" note corrected to 58 speaker-label-only plus 18 real.

**Result.**
- `[UI]`: `public/verses` differing from `verses.jsonl` 0. Components reading `shlokaDirectory` text 0. 60 speaker labels, paired in Sanskrit and IAST.
- The TS splitter run on all 701 verses agrees with the check.
- Build, lint and the 330 tests pass.

**Side note.** Reading verseStore's module cache during render made the React Compiler skip `GitaBookReader` (oxlint `preserve-manual-memoization`). Loaded chapters now live in component state.

---

## 2026-11-19 · Chat UX B2 + B3: composer, scrolling, answer layout

**Problem.**
- The question box was a single-line `<input>`, disabled while loading.
- The chat always jumped to the end of long answers.
- The line-by-line formatter didn't render lists and split quotes into one box per line.
- The verifier's "unsupported statement removed" warning was shown as an amber "quotes could not be checked".

**Fix (files).**
- `components/chat/ChatComposer.tsx`:
  - auto-growing textarea; Enter sends, Shift+Enter adds a line
  - IME-safe: no send while `isComposing` or on keyCode 229
  - 1000-character cap with a counter from 800; 16px text on mobile
  - stays editable while loading, and Stop replaces Send
- `components/chat/useChatScroll.ts`:
  - follows new messages only when at the bottom
  - a new long answer opens at its first line
  - "Jump to latest" button
  - instant scroll when the distance is more than two screens
- `components/chat/markdown.ts` + `AnswerMarkdown.tsx`:
  - headings, nested lists, grouped quotes (Devanagari / IAST / prose styled separately), bold, italic, code
  - Copy produces plain text with no Markdown symbols
- `components/ChatPanel.tsx`:
  - centered 760px column; answers full width without a card
  - user messages in a cream `#F4ECE1` bubble with a gold border (12.77:1 contrast)
  - quiet warning notes (repeated "removed" warnings are counted)
  - Copy in an action row under the answer

**Result.**
- Build, lint and the 330 tests pass.
- Checked in the browser with a stubbed `/api/ask`: Shift+Enter, auto-grow, Stop, scrolling, the jump button, list and quote rendering, Copy text, and 375px.

**Dev note.** After renaming `markdown.tsx` to `markdown.ts`, the running Vite dev server kept requesting the old file (404, blank page) until it was restarted. The production build was unaffected.

---

## 2026-11-19 · Live test fixes: verse cards, explained answers, no allusions

**Problem (owner's live test, interview-fear question).**
- Verse cards had no English, and the player repeated the Sanskrit.
- Answers quoted a verse but didn't explain it.
- An answer alluded to BG 2.14 ("pleasure and pain are transient"), which wasn't in context.
- Only BG 11.49 was cited.
- "Jump to latest" covered verse cards.

**Root cause.**
- Prompt rule 9 capped commentary at 3 sentences per sub-question, and a later bullet allowed "at most one plain sentence" after a quote.
- No rule forbade uncited allusions.
- For a reconstructed version of the question, retrieval returned 12.8, 11.49, 6.10, 1.29 and 12.11. No topic boost covers fear or results, so none of the results verses (2.47, 2.48…) were retrieved.
- The UI showed a different translator from the prompt's for 580 of 701 verses: `public/translations` reorders authors, while the prompt sends `english[0]`.

**Fix (files).**
- `frontend/scripts/export_verses.py`: exports `translation` = `english[0]`. Chat cards (`chat/VerseCardTranslation.tsx`), the verse modal and the quote card show it.
- `ClipPlayer.tsx`: `compact` mode, used by the chat cards.
- `ChatPanel.tsx`: list bottom padding (`pb-14`), and the jump button is now a 36px round icon in the corner.
- `backend/retrieval/prompt_v2.py`:
  - rule 9 now asks for who speaks → plain meaning → application, explaining 2 verses when two fit
  - length 180-220 words (single question) or about 120 per section (300 max)
  - new no-allusion bullet; `LENGTH_REMINDER` updated
- Tests: `test_quote_verification.py` assertion updated. New `test_answer_structure_prompt.py` with fixture `tests/fixtures/allusion_2_14.json`; its live test is skipped unless `VYOM_LIVE_LLM=1`.

**Result.**
- 333 passed, 1 skipped. The live allusion test passed once (one LLM sample).
- Real answers, run outside the server against a copy of the index:
  - before the length fix: 2,252 prompt + 200 completion tokens, 123 words
  - after: 2,267 + 255 tokens, 175 words, still only one verse explained because the retrieved set had nothing on results or fear
- The topic map is proposed and not wired; it waits for owner review.

---

## 2026-11-19 · Live test round 2: false premises, quote-first answers, small talk

**Problem.**
- "celibacy in the Karthik month" got an answer implying the Gita teaches a Kartik practice.
- Answers paraphrased verses loosely:
  - 10.35 merged its months and seasons
  - 8.24/8.25 were called "a ritual"
  - 3.43 had "selfless action" added
- "hi" cost about 2.5K tokens and returned a 180-word sermon.

**Root cause.**
- No rule existed for false premises. Retrieval for "month" also pulls 8.24 and 8.25 ("six months before the solstice"), which is likely where the "ritual" paraphrase came from.
- The verifier checks only quotes of 5+ words (`extract_quotes(min_words=5)`), so short or missing quotes go unchecked.
- Every message went to retrieval and the LLM.

**Fix (files).**
- `backend/retrieval/prompt_v2.py`:
  - rule 9 is now quote-first (a key phrase of at least 6 verbatim words, then who speaks, meaning, application)
  - new rule 11 (false premises, using the fixed sentence "The Gita says nothing about X.")
  - new rule 12 (faithful wording: no synonym swaps, no merged list items, no "ritual/path" labels, no glosses, no "broader Gita")
- `backend/retrieval/premise.py` (new), called from `verify_and_clean_answer(query=...)`. When a month, festival or observance in the question is in no shown verse, a sentence pairing it with a citation is removed (with a warning). The "says nothing about" sentence only loses its citation.
- `backend/retrieval/smalltalk.py` (new) plus a check at the top of `/api/ask`: greetings, thanks, "who are you" and fillers get a fixed reply with no retrieval or LLM call. `routed` is `"smalltalk"` and the `X-VYOM-Route` header is set.
- Frontend:
  - `SuggestionChips` appear under the small-talk reply
  - "Jump to latest" moved into the input bar, replacing the footnote while scrolled up, so it no longer covers cards
  - no left-edge clipping reproduced at 768, 900, 1024 or 1180px
- Tests: `test_premise_and_wording.py`, `test_smalltalk.py`, fixture `paraphrase_regressions.json` (live cases are opt-in).

**Result.**
- 382 passed, 5 skipped.
- Live regressions: 10.35, 8.24 and 8.25 pass. 3.43 still says "selfless action" after two prompt tightenings.
- 2.28 was dropped as a case: the translation the prompt shows (Adidevananda) itself says "unknown beginning…".
- "Garatri" is in the dataset's 10.35 translation (data, not LLM).
- Re-run on a second backend at :8001 with the current code:
  - "hi": small-talk route, no LLM call
  - Karthik: starts with "The Gita says nothing about the Karthik month", quotes 6.14 and 17.14 verbatim (2,821 + 339 tokens)
- The owner's :8000 server was still on the old code (it served the old "hi" sermon from cache) and needs a restart.

---

## 2026-11-19 · Life-theme map wired; boosted parts of multi-part questions kept

**Change.** `retrieval/topic_boost.py` has the owner-approved life themes:
- results (replaces "failure"), fear, guilt, desire, grief, anger, confusion and duty
- celibacy extended with 2.59 and 2.60
- whole-word triggers, plus the misspellings seen in live questions ("celabacy", "fearning", "tensed")
- `LIFE_THEMES` are cut to the concept cap (3) when a question has 2+ sub-questions; contested topics are never cut

**Problem.** In the owner's 3-part question, the celibacy part lost all its boosted verses.

**Root cause.** Boosted verses score just below their own part's best hit. The desire and guilt parts scored higher and took every shared fill slot.

**Fix.** In `retrieval/multi.py`, a boosted part's first boosted verse is now one of its two guaranteed picks. Test: `test_life_themes_and_english_fix.py`.

**Also.**
- 3.43 live regression marked xfail (owner: "selfless action" accepted).
- `ENGLISH_CORRECTIONS` in `clean.py` fixes Garatri → Gayatri (10.35, Shri Purohit Swami). Data regeneration and re-index are pending (CLAUDE.md).
- `test_chunk.py` applies pending English corrections to the saved chunks before comparing.

**Result.**
- 405 passed, 5 skipped.
- The owner's :8000 process (started 19:26, no --reload) predates these edits, so the re-runs used a current-code backend on :8001 with a copy of the index.
- Interview question: 2.47, 2.48, 2.38, 2.14, 18.66, 2.56, 2.40 and 12.15 retrieved. The answer explains 2.47 and 2.48. 3,273 + 269 tokens.
- 3-part question: 6.14 now kept. Remaining issues:
  - the guilt part quotes 18.6 as if regretted acts lose their binding power, which 18.6 does not say, although 4.36, 9.30 and 9.31 were in context
  - the celibacy part ties 6.14 to "the Karthik month" in an uncited sentence that the premise guard can't see
- "karthik month": opens with "The Gita says nothing about the Karthik month". 2,967 + 381 tokens.
- "hi": small-talk route, no LLM call.

---

## 2026-11-19 · Theme verses first, 6-verse cap, B4–B6

**Problem.**
- In a 3-part question, the guilt part quoted 18.6 as if regretted acts lose their binding power, although 4.36, 9.30 and 9.31 were in context.
- The prompt was large: about 3.3K tokens for a single question.

**Root cause.**
- Boosted verses scored just below the best semantic hit, so loosely related matches (18.6, 18.9) were listed first.
- The global 12-verse cap refilled every freed slot with semantic matches.

**Fix (files).**
- `topic_boost.py`: life themes + concepts share `MAX_THEME_BOOSTS = 6` per sub-question (round-robin); contested topics are never cut.
- `multi.py`: boosted verses are marked `theme_for`, and a themed sub-question isn't topped up with more semantic matches.
- `prompt_v2.py`:
  - `theme_verses_first()` and the "Theme verse for Sub-Question N" label
  - a rule to explain a theme verse in that section
  - the multi-answer false-premise sentence
- Frontend:
  - B4: `chat/AssistantAnswer.tsx` + `chat/VerseCard.tsx` (inline BG chips → open group, scroll, 1.2 s highlight; collapsible groups; quote-card button)
  - B5: start screen instead of the stored welcome; `?debug=1` badge; block-staggered ≤600 ms reveal for new answers
  - B6: Esc stops; `aria-live` announcement; global `:focus-visible` outline; `interactive-widget=resizes-content` + safe-area padding

**Result.**
- 406 passed, 5 skipped. Build and lint pass.
- One live run of the 3-part question: the guilt part now quotes 9.30 (3,413 + 535 tokens).
- Question 1 estimated offline: from 12 to 7 verses, about 2,990 prompt tokens, against about 3,273 measured before. The ~2,800 target isn't met because the system prompt alone is about 2,218 tokens.
- The owner's :8000 process ran without `--reload` (its command line), so that live run used a current-code backend on :8001.
- The owner's two test questions were removed from tests, backups, caches and run outputs.

---

## 2026-11-20 · Final: re-index for the 10.35 English fix, chat UI summary, code freeze

**Re-index (Garatri → Gayatri, 10.35, Shri Purohit Swami).**
- Before regenerating, the raw pipeline was diffed in a temp folder: exactly one change in `verses.jsonl` (10.35 `translations.english[0].text`) and one in `chunks.jsonl` (`10.35:v` `embed_text`).
- Backups: `verses.jsonl.bak2`, `chunks.jsonl.bak2`, `embeddings.bak2`, `qdrant_data.bak2`, and the previous `public/verses` and `public/translations` copies.
- `ingestion/chunk.py` regenerated both files; `check_pipeline_repro.py` reports byte-identical.
- Both models were re-embedded and re-indexed (`embed.py` + `build_index.py`): `vyom_bge_m3` and `vyom_bge_base` each have 1,569 points.
- The `10.35:v` payload in both collections says "Gayatri". Only that vector changed; the other 1,568 match the backup.
- Both frontend exports were re-run: only `ch10.json` changed in each folder.
- `test_life_themes_and_english_fix.py` now rebuilds the raw typo itself before testing the correction, because the served data no longer has it.

**Chat UI work, B1–B6 (frontend unless noted).**
- **B1:**
  - no invented "offline" answers; typed errors with Retry, Stop via AbortController
  - debug headers read from the response
  - verse lookup for all 701 verses from canonical data (`verseStore.ts`, `export_verses.py`)
- **B1.5:**
  - the Sacred Book reads canonical text; the hand-written `gitaVerses.ts` entries are removed
  - speaker labels split off for display
  - `check_sanskrit.py` `[UI]` lines show 0 of the 18 directory mismatches
- **B2:** auto-growing composer (Enter / Shift+Enter, IME-safe, 1,000-character cap); follow-or-stay scrolling, with "Jump to latest" in the input bar.
- **B3:** centered 760 px column, unbubbled answers, cream user bubble (12.77:1 contrast); a small Markdown renderer with nested lists and grouped quotes; Copy gives plain text; quiet warning notes.
- **B4:** `(BG x.y)` chips open the verse's collapsible group, scroll to it and highlight it once; a verse without a card opens the verse modal; compact player; the card shows the prompt's own translation and translator.
- **B5:** start screen instead of a stored welcome; `?debug=1` badge (cache / provider / model); block-staggered ≤600 ms reveal for new answers only.
- **B6:** Esc stops a running answer; `aria-live` announcement; global `:focus-visible` outline; `interactive-widget=resizes-content` and safe-area padding.
- **Backend work alongside**, at the owner's request:
  - quote-first explain-each-verse prompt, false-premise and faithful-wording rules
  - `premise.py`, small-talk route, life-theme boosts (6-verse cap, theme verses first)
  - multi-part pick fix, `ENGLISH_CORRECTIONS`

**Freeze.** Code is frozen from 2026-11-20: no prompt or retrieval changes. The remaining limitations are listed in README "Known limitations": paraphrase drift, false-premise placement in multi-part answers, about 2 new questions per minute on Groq's free tier, the small eval set, Hinglish in Latin script not being routed, and the untrimmed ~2.2K-token system prompt.

**Result.** 407 passed, 5 skipped. Frontend build and lint pass. `check_sanskrit.py` `[UI]` lines: 0 / 0 / 60 paired.

---

## 2026-11-20 · Sacred Book button hard to find on phones

**Problem.** On a phone (375 px) the owner couldn't find the Sacred Book.

**Root cause.** The navbar button hid its label below 768 px (`hidden md:inline`) and used a headphones icon, so it read as an audio control next to the music button. It had no `aria-label`. The sidebar's "Explore All 701 Shlokas" sits below the chat on phones.

**Fix (files).** `components/Navbar.tsx` (backup `.bak1`): book icon, a visible "Book" label on phones ("Sacred Book" from 768 px), and `aria-label="Open the Sacred Book"`.

**Result.** At 375 px the header fits with no overflow, and tapping "Book" opens the Sacred Book cover. Build and lint pass. Frontend only; no prompt or retrieval change.

---

## 2026-11-20 · Sacred Book on phones: two stacked pages

**Problem.** On a phone the open book showed only the Sanskrit page. The English page sat below it in one long scroll inside the book, so it read as a single page.

**Root cause.** In the phone CSS (`GitaBookReader.css`, max-width 767 px), the Sanskrit page had `min-height: clamp(340px, 48dvh, 510px)`, the spread scrolled as one column, and there was no gap between the pages. Separately, `.gita-sanskrit-content` centered with `justify-content: center`, which pushes the first lines of a too-tall verse above the scroll area where they can't be reached.

**Fix (files).** `components/GitaBookReader.css` (backup `.bak2`):
- Phones: the spread is a column of two equal pages (`flex: 1 1 0`), Sanskrit on top and English below, with a 9 px spine gap showing the cover. Each page scrolls inside itself. Page shading runs towards the spine.
- Phones: smaller Sanskrit font (`clamp(1.2rem, 5.6vw, 1.6rem)`); the ornament and the duplicate footer page number are hidden.
- All widths: the verse is centered with auto margins instead of `justify-content: center`, so overflow stays scrollable.

**Result.**
- 375×812: two 234 px pages, both on screen.
- 360×740: two 198 px pages.
- No outer or sideways scroll at either size.
- Desktop looks the same: side-by-side spread, centered verse, ornament and page numbers shown.
- Build and lint pass. CSS only.

---

## 2026-11-20 · Sacred Book: mobile reading layout

**Problem.** With two half-height pages, each scrolling on its own, a phone showed only a slice of the verse and of the meaning. The recitation button sat at the end of the English page, out of reach, and the toolbar took three rows (about 170 px).

**Fix (files).** `components/GitaBookReader.tsx` (backup `.bak2`) and `GitaBookReader.css` (backup `.bak3`), phones below 768 px only:
- **Reading:** the two pages stay stacked with the spine gap but take their full height, and the folio scrolls as one, so the verse and then its meaning read top to bottom. A new verse starts at the top. The ornament is back; the duplicate footer number is hidden. Larger Sanskrit, IAST and English type.
- **Bottom bar:** Prev, a central "Play 1.1" recitation button (maroon `.vyom-play-button`, through `audioCoordinator`) and Next. All 44 px, clear of the safe area.
- **Toolbar in one row:** back, Contents (icon), chapter picker, a search icon that toggles the verse search row (which closes after Go), and Cover. The title row is hidden on phones. 64 px instead of about 170 px.
- **Swipe:** a horizontal swipe of 60 px or more on the book goes to the next or previous verse; vertical drags are ignored.
- **Trap found:** the unlayered `.vyom-play-button { display: inline-flex }` in `index.css` overrides Tailwind's layered `md:hidden`, so the button sits in a wrapper that carries `md:hidden`.

**Result.**
- 375×812: toolbar 64 px, Play always visible, scroll 569 / 928 px, no sideways scroll.
- Checked: swipe → 1.2 with the scroll reset, vertical drag ignored, search → 2.47, Play → "Pause 2.47" (background music paused).
- 768 and 1024+: spread side by side, unchanged.
- No console errors. Build and lint pass. Frontend only; no new colours, fonts or animations.

---

## 2026-11-20 · Reusable scripts moved to tracked backend/scripts/

**Change.**
- Moved ten scripts from the gitignored `backend/_scratch/` to a new tracked `backend/scripts/`: `warm_cache`, `failover_check`, `measure_ask`, `hindi_check`, `concept_router_eval`, `hard_queries_latency`, `check_pipeline_repro`, `verify_reindex`, `gemini_diag`, `groq_models`.
- `patch_*`, logs, JSON outputs and the rest stay in `_scratch` (still ignored).

**Fixes.**
- Hardcoded `D:\VYOM-AI\backend` paths in `failover_check`, `measure_ask`, `gemini_diag` and `groq_models` now resolve from the script's location.
- Usage lines now say `backend\scripts\`.
- The two eval scripts still write their JSON to `_scratch/`.
- `verify_reindex.py` skips its backup comparisons when the backup is missing. `QdrantClient(path=...)` silently creates an empty database at a missing path, and the first run created an empty `qdrant_data.bak1`, which was removed.

**Found.** The Qdrant backups `qdrant_data.bak1` and `qdrant_data.bak2` (the 2026-11-20 pre-reindex copy) were no longer on disk before this task. The `verses`, `chunks` and `embeddings` `.bak` files remain, so Qdrant can be rebuilt from them.

**Secrets.** No `gsk_`, `AIza` or `api_key="…"` literals in the moved scripts; keys are read only from `backend/.env` or the environment.

**Docs.**
- README (warm cache, repro check, plus `verify_reindex` and the utilities list), CLAUDE.md, `docs/BENCHMARK.md` and the `sanskrit-data` skill now point to `scripts/`.
- `.gitignore` no longer ignores `frontend/public/translations/`.

**Result.**
- Run from the new folder: `warm_cache.py --list` (chip map printed), `check_pipeline_repro.py` (byte-identical) and `verify_reindex.py` (1,569 points ×2, fixed verses 6/6, retrieval OK).
- All ten compile. 407 passed, 5 skipped. Build and lint pass.
