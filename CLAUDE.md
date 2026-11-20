# CLAUDE.md — VYOM

VYOM is a Bhagavad Gita question-answering app. The backend is FastAPI with
dense search over Qdrant (bge-base, bge-m3 for Devanagari), multi-query
retrieval, Groq generation and a quote verifier. The frontend is Vite, React and
TypeScript, with an animated ember gateway (canvas, `VyomGateway.tsx`), a
cream-and-gold sanctuary dashboard, the Sacred Book reader and per-shloka
recitation clips.

## Hard rules
1. **Never run git.** No commit, add, push, checkout, stash, reset, or branch
   operations. Read-only inspection is also off unless I ask. I do all git.
2. **Inspect first, change second.** Before editing, read the relevant files
   and say what you found and what you plan to change. For anything beyond a
   trivial fix, wait for my OK.
3. **Flag unverified claims.** When you state something about the code, data
   or runtime, mark it CONFIRMED (you checked it in code or output), or
   UNVERIFIED (assumed, or not checkable without a live call). If the code
   disagrees with me or with a doc, the code wins. Tell me.
4. **The backend is frozen** (`backend/`) unless the task explicitly says
   otherwise. That includes data files, indexes, `qdrant_data/` and `.env`.
   Report backend problems; don't fix them.
5. Never print or copy secrets from `.env` files.

## Layout
- `backend/api/main.py` holds `/api/ask` and `/api/health`. `api/clips.py`
  mounts `/audio` (from `backend/data/multimodal/source/assets/audio`) and
  attaches clips to sources.
- `backend/retrieval/` holds search, multi-query (`multi.py`), prompts
  (`prompt_v2.py`), the router and `verify_quotes.py`.
- `backend/llm/client.py` tries providers in the order set by `LLM_PROVIDERS`
  (default groq, groq2, gemini, ollama). `groq` is gpt-oss-120b; `groq2`
  is `GROQ_FALLBACK_MODEL` (default `openai/gpt-oss-20b`, which has its own
  per-model rate limit). One Groq client is reused across calls with
  `max_retries=0`; a 429 retries once only if retry-after <= 5 s, otherwise
  that provider cools down and the next one is tried. Gemini is called over
  plain REST (httpx), not an SDK.
  The Groq model defaults to `openai/gpt-oss-120b` (llama-3.3-70b is
  Enterprise-only now). gpt-oss always reasons: every call sends
  `reasoning_effort="low"`, `include_reasoning=False`, `max_tokens=1000`.
- `backend/data/processed/verses.jsonl` is the canonical verse text (701).
- `backend/data/multimodal/verse_clips.json` maps verse IDs to recitation
  clips (700 verse mp3s plus 18 chapter mp3s).
- `frontend/src/services/audioCoordinator.ts` makes playback exclusive and
  pauses background music while a clip plays.
- `frontend/src/data/shlokaDirectory.json` and `recitationIndex.ts` drive the
  reader's navigation order and recitation audio only. No component reads
  verse text from them.
- Verse text in the UI (chat cards, verse modal, quote card, Sacred Book)
  comes from `frontend/src/data/verseStore.ts`, which loads two generated
  per-chapter files. Never hand-edit either; rerun its script:
  - `frontend/public/verses/chNN.json` (Sanskrit, IAST, word meanings) ←
    `frontend/scripts/export_verses.py` from `verses.jsonl`.
  - `frontend/public/translations/chNN.json` ←
    `frontend/scripts/export_translations.py` from `verses.jsonl`.
- `frontend/src/utils/speaker.ts` splits speaker lines ("अर्जुन उवाच") off
  for display as a small label. The data is not changed.
- `backend/scripts/` (tracked) holds the reusable utilities: `warm_cache.py`,
  `failover_check.py`, `measure_ask.py`, `hindi_check.py`,
  `concept_router_eval.py`, `hard_queries_latency.py`,
  `check_pipeline_repro.py`, `verify_reindex.py`, `gemini_diag.py`,
  `groq_models.py`. Keys come only from `backend/.env`. The two eval scripts
  write their JSON results to `backend/_scratch/`.
- `backend/_scratch/` (gitignored) and the `*INTEGRATION_NOTES*.txt` files are
  historical: one-off patches, logs and outputs. Both integration patches are
  already applied in `main.py`.

## Commands
`venv/` is a conda environment, so the interpreter is `venv\python.exe`.
There is no `venv\Scripts\python.exe`.
- Backend tests: `.\venv\python.exe -m pytest backend/tests` (407 passed,
  5 skipped as of 2026-11-20; the skipped ones are opt-in live LLM tests,
  run with `VYOM_LIVE_LLM=1`).
- Run both servers on Windows: `npm run dev:win` (backend :8000, frontend
  :5173; Vite proxies `/api` and `/audio`).
- Frontend build or type-check: `npm run build`.
- Lint: `npm run lint:frontend`.

## Retrieval at serve time
- Embedding model: `VYOM_EMBED_MODEL` (default `bge-base`, which won the
  English benchmark in `docs/BENCHMARK.md`). Queries containing Devanagari
  go to `bge-m3` (`VYOM_SCRIPT_ROUTING`, default on; costs about 300 MB RAM).
  `/api/health` reports both.
- `retrieval/concepts.py` is a hand-curated concept router (16 Sanskrit
  terms -> verses), applied through `topic_boost.boost_verses`. It is not
  part of the retrieval benchmark numbers.
- `topic_boost.py` also has owner-approved life themes (results, fear, guilt,
  desire, celibacy, grief, anger, confusion, duty; whole-word English
  triggers). Life themes + concepts share at most 6 boosted verses per
  sub-question (round-robin, each keeps its first verse; 3 each with 2+
  sub-questions). Contested topics (caste, war...) are never cut. Boosted
  verses are marked `theme_for`, listed first in the prompt as "Theme verse
  for Sub-Question N", and a themed sub-question is not topped up with more
  semantic matches (`multi.py`).
- `/api/ask` answers small talk ("hi", "thanks", "who are you") with a
  fixed reply and no retrieval/LLM call (`retrieval/smalltalk.py`,
  `routed="smalltalk"`). `retrieval/premise.py` removes citations attached to
  a question's false premise (months, festivals, observances).
- The user-level format-on-edit hook only formats files under `frontend/`
  in this repo (`.claude/settings.json` sets `FORMAT_ON_EDIT_ONLY`).
  Backend Python is never auto-formatted.

## Known issues
- Git is blocked two ways since 2026-11-19: a permissions deny in
  `.claude/settings.json` (`Bash(git:*)`, `Bash(git *)`) plus hard rule 1.
  Before that date no settings file existed, so it was instruction only.
- `shlokaDirectory.json` differs from `verses.jsonl` in 76 verses: 58 only
  by a speaker label and 18 real text mismatches (17 half-verse shifts in
  chapters 1, 4 and 6, plus 18.66). The old note said 80. The backend copy is
  canonical. Since 2026-11-19 the UI shows none of them, because it no longer
  reads the directory's text (`check_sanskrit.py` `[UI]` lines). Audio
  alignment must be checked before any text fix in the directory.
- Gemini: gemini-2.5-flash and -lite return 404 "no longer available to
  new users"; `gemini-3.5-flash-lite` works (checked 2026-11-19). The code
  default and `.env.example` use it, but `backend/.env` still sets
  `GEMINI_MODEL="gemini-2.5-flash"` until the owner edits it; until then
  Gemini is marked dead after its first 404.
- Ollama is not installed, so the last fallback is not available.
- Sanskrit typo fixes (1.26, 1.34, 4.29, 4.31, 9.25, 10.29) live in
  `SANSKRIT_CORRECTIONS` in `backend/ingestion/clean.py`, and one English fix
  (10.35 Shri Purohit Swami "Garatri" → "Gayatri") in `ENGLISH_CORRECTIONS`,
  so the raw pipeline reproduces `verses.jsonl` and `chunks.jsonl` byte for
  byte. Qdrant (both collections, 1,569 points each) was last rebuilt from
  them on 2026-11-20 (backups `qdrant_data.bak1`, `qdrant_data.bak2`).
  `test_chunk.py` applies any English correction not yet regenerated into
  `chunks.jsonl`; today there are none.
- Groq rate limits on this account: 8K tokens/minute, 1K requests/day
  (from response headers; docs also list 200K tokens/day). With the
  explain-each-verse prompt (system prompt ~2.2K tokens) a new question
  sends about 2.9-3.4K prompt tokens plus 250-600 completion tokens, so about
  2 new questions per minute; repeats come from the in-process answer cache
  (`backend\scripts\warm_cache.py` warms it for demos).
- Code is frozen as of 2026-11-20 (chat UI B1-B6 done): no prompt or
  retrieval changes without the owner's go-ahead.
- `RecitationSanctuary.tsx` is not mounted anywhere.
- `font-cinzel-dec` points at Cinzel Decorative, which is not loaded.
