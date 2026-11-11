# VYOM Handoff — 11 Nov 2026

Next session, tell Claude Code: "Read CLAUDE.md and docs/HANDOFF.md, verify the status against the repo, then start with Next steps #1."

## Rules (unchanged)

- Claude Code never runs git (hard-blocked in `.claude/settings.json`). I do all git.
- Inspect first, change second. Flag claims CONFIRMED or UNVERIFIED.
- Backend frozen unless the task lifts it for specific files.
- Formatter hook reformats whole files; patch backend via scripts. TODO: scope hook to `frontend/`.

## Done on 11 Nov

- `CLAUDE.md` written. Skills in `.claude/skills/`: `vyom-ui`, `sanskrit-data` (+ `check_sanskrit.py`), `verify-before-done`.
- Tests: `.\venv\python.exe -m pytest backend/tests` (conda venv, not `venv\Scripts`). Baseline 228/228 (172 before session 2, 196 after it).
- `dev:win` fixed to use `venv\python.exe`.
- Security: multi=true path no longer leaks raw exception text (masked 503, logged server-side). Test proves it.
- Data: 6 Sanskrit typos fixed in `verses.jsonl` (1.26, 1.34, 4.29, 4.31, 9.25, 10.29). 18.66 "त्वा" kept as a valid reading. Backup `verses.jsonl.bak1`. Qdrant not re-indexed.
- Cleanup: `audioChant.ts` deleted, three.js deps removed, AboutModal copy rewritten.
- Single-verse questions ("Explain BG 2.47") now use the v2 prompt + shared `verify_and_clean_answer()`. Referenced verse gets one commentary excerpt; quotes from it are accepted. Replaced quotes use the best-matching translation.
- No-meta rule replaces exact-phrase bans ("supplied/provided/retrieved").
- LLM: actually `openai/gpt-oss-120b` (llama-3.3-70b is Enterprise-only, was a silent failing call). Now `reasoning_effort: low`, `include_reasoning: false`, `max_tokens 1800`. Reasoning 779 → 175 tokens; no more "(answer shortened)".
- Answers: one `### n.` section per sub-question, each placed above its own verse cards. Nearby verses capped at 3. Duplicate-send guard added.
- UI: source cards use a "Play verse" button via `audioCoordinator`; IAST uses `.iast` (Georgia italic) instead of Cinzel; welcome chips say "Begin with".

## Done on 11 Nov (session 2)

Backend freeze lifted only for `retrieval/router.py`, `retrieval/multi.py`, `retrieval/prompt_v2.py`, `api/main.py`.

- All verse refs in a question are now retrieved (`parse_verse_refs`). Ranges like `2.19-2.20` / `2.19–20` expand to max 5 verses; forced refs max 6 per request (`FORCED_REFS_TRUNCATED` logged); total context still 12.
- Routing: only one ref in a single-topic question uses the single-verse path; any other ref question goes through decomposition, with each referenced verse forced into its own sub-question (`VERSE_REFS_FOUND`, `ROUTE`, `FORCED_REFS` logs).
- "chapter 12" no longer routes to 1.2 (it now takes the semantic path); "approach 13.7" no longer routes to 1.3.
- Chapter 13: a 13.N ref also brings 13.(N+1), tagged "in the 700-verse numbering, this verse is 13.N". No silent remapping.
- Prompt: "cite only verses shown above"; unaddressed topics use "The text doesn't address this directly."; rule 4 examples use `(BG X.Y)` placeholders instead of 16.21 / 18.17.
- `rewrite_gita_does_not` no longer injects "The verses retrieved for this question…".
- Tests: `backend/tests/test_verse_refs.py` (24 tests).

## Next steps (in order)

0. Rerun retrieval eval before quoting any numbers — parse_verse_ref changed.

1. Browser check of the latest round: moksha question shows 3 sections with cards below each, no "(answer shortened)", no "paraphrase"/"my inference"; nearby verses ≤ 3; "Explain BG 2.47" uses normal layout; repeat at 375px. Also check `VerseDetailModal` Sanskrit isn't invisible (`#FFF8E7` on ivory).
2. Commit in logical chunks. Make sure `*.bak*` is in `.gitignore`.
3. Rate limits (demo risk): free tier ~8K TPM → ~1 question/min, ~34/day. Plan:
   - remove the duplicated instructions block (978 tokens) from the user message
   - static prompt prefix first for caching (cached tokens don't count)
   - drop IAST from the LLM prompt only (545 tokens)
   - LRU response cache keyed by normalized question, with a cache-hit header
   - fix Gemini 404 (`.env` 2.5-flash vs code default 1.5-flash) so Groq 429 fails over; header showing which provider answered
   - re-measure tokens/question, latency, questions/min; re-check sub-question 2 ignoring "Relevant to" and sub-question 3 overgeneralizing
4. Listen to 12 clips in `backend/data/multimodal/source/assets/audio/verses/`: bg_01_20, 01_22, 01_26, 01_33, 01_36, 01_37, 01_46, 04_29, 04_31, 06_23, 06_24, control 02_47.
5. Then regenerate `shlokaDirectory.json` from `verses.jsonl` + `verse_clips.json` (approved plan steps 1-3): `clips[]` with `partial` flag, "recited together with" note, separate `speaker` field (fixes 58 speaker-line cases incl. BG 1.1 transliteration). No audio re-cutting.
6. Decide: mount or delete `RecitationSanctuary` (currently unmounted).
7. Book cover (`frontend/public/bookcover.png`, actually a JPEG): source/license unknown. Replace if unsure.
8. Audio feature: recommended "recite a shloka → find the verse" (Whisper → normalized fuzzy match over 701 verses), with a small top-1/top-5 eval. Alternatives: voice questions, video phase.
9. `docs/PROJECT_HISTORY.md` + benchmark table (six configs × v2 strict/lenient, numbers from `retrieval/eval/results`, none invented).
10. Later: re-index Qdrant after typo fix; Cinzel on answer `###` headings; 18.66 transliteration says "tvāṁ" vs Devanagari "त्वा"; 3 lint warnings; >500 kB bundle.

## Demo-day reminders

- Don't burn the daily token budget testing that morning.
- Demo queries: "Nishkama Karma in Modern Life" chip, "How to master an agitated mind?", "Explain BG 2.47".
