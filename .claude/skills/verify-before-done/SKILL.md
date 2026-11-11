---
name: verify-before-done
description: Use before saying any VYOM task is finished, fixed or working.
---

1. Backend, from the repo root in PowerShell: `.\venv\python.exe -m pytest backend/tests -q`. Baseline: 228 passed (172 + 24 in test_verse_refs.py + 32 in test_grounding_cleanup.py, 2026-11-12).
2. Frontend, in `frontend/`: `npm run build`, then `npm run lint`. Baseline: build OK (the >500 kB chunk warning is normal); lint 0 errors and 3 warnings (App.tsx `purity` and `set-state-in-effect`, SuggestedChips `only-export-components`).
3. If verse or clip data changed, run the sanskrit-data check script and compare with its baseline.
4. Report the real counts from the output and how they differ from baseline. Never round them or assume.
5. When a fix intentionally changes a baseline number, update the baseline in this skill (or in sanskrit-data) in the same task and say so in the report.
6. List everything that can only be checked in a browser as UNVERIFIED, with exact steps: `npm run dev:win`, open http://localhost:5173, what to click, what should happen, and the same at 375px width in DevTools.
7. Never say something works in the browser until the owner confirms it. Never run git.
