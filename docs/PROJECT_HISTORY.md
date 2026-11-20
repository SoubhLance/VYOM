# VYOM project history

A short record of how VYOM got to its current shape and why. For the detailed problems and numbers see [CHALLENGES_LOG.md](CHALLENGES_LOG.md); for the retrieval evaluation see [BENCHMARK.md](BENCHMARK.md).

Dates are file last-modified dates or dated notes in the repo, so each one marks when that piece last changed, not when work on it began.

## Timeline

| When | Milestone |
|---|---|
| Before Oct 2026 | **GyaanVaani**, the predecessor project (per the owner; none of its files are in this repository). |
| 17 Oct 2026 | Bhagavad Gita dataset added (`backend/data/gita`): 701 verses, 7 translations, 16 commentaries. |
| 20 Oct 2026 | Cleaning and chunking pipeline (`clean.py`, `chunk.py`): 1,569 chunks. bge-m3 and bge-base embeddings, local Qdrant index, first dense retrieval eval. |
| 23 Oct 2026 | Hybrid retrieval (BM25 + dense, RRF) with `--stopwords` and `--expand-always` variants. |
| 24 Oct 2026 | Blind pooling of 225 verses and judging, giving strict and lenient gold sets (`questions.v2*.jsonl`). |
| 2 Nov 2026 | Multi-question answering, the v2 prompt and the quote verifier. Recitation audio cut into 700 verse clips and 18 chapter clips (`verse_clips.json`). |
| 11–12 Nov 2026 | Project rules (`CLAUDE.md`) and skills. Answers grounded in retrieved verses, verse-reference routing, 6 Sanskrit typo fixes. Frontend: verse play buttons, gateway and book cover (see `HANDOFF.md`). |
| 19 Nov 2026 | Finishing sprint: Groq token diet and failover, Gemini over REST, re-index, benchmark re-run, serving switch to bge-base, Devanagari routing, concept router, docs. |

## Key decisions

- **Rename GyaanVaani to VYOM.** Per the owner; the reason isn't recorded in the repository.
- **Groq as the main LLM.** The repository doesn't record why it was chosen; the logs show the effect: about 0.7 s of server time per answer.
  - `openai/gpt-oss-120b` replaced llama-3.3-70b, which became Enterprise-only and was silently failing.
  - Low reasoning effort keeps hidden reasoning tokens from eating the answer.
- **Quote verifier on every answer.** A model can invent a quote that looks like scripture. Quotes of 5+ words must match a translation or commentary excerpt the model was shown; otherwise they are replaced or their sentence is removed. It runs for every provider, not just Groq.
- **Audio cut at slide changes, not pauses.** Pause-based splitting failed on the source recording, but its slides change about once per verse, so verse boundaries come from ffmpeg scene detection (`gita_split_slides.py`).
- **Eval-driven retrieval.** Configurations were judged on a blind, pooled, hand-reviewed gold set instead of by eye.
  - That showed hybrid BM25 didn't beat dense retrieval, and why: lexical noise, fusion demoting Sanskrit-term hits, and inconsistent IAST spellings.
  - It led to serving with dense bge-base.
- **Devanagari queries go to bge-m3.** bge-base is English-only and fails on Hindi in Devanagari.
- **A hand-curated concept router instead of more retrieval tuning.** Bare Sanskrit terms (sthitaprajna, svadharma) never reached their defining verses with any retriever. A small, owner-approved map of 16 terms fixes that, and it stays out of the benchmark numbers.
- **Sanskrit fixes live in the pipeline, not in generated files.** Hand edits to `verses.jsonl` would be undone by the next pipeline run. Corrections are a table in `clean.py` that fails loudly if the source text changes.
- **No retrieval or LLM work in the browser.** The frontend only renders: verse cards, Sanskrit and clips come from the API, and all audio goes through one coordinator so only one sound plays at a time.
