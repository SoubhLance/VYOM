"""Answer structure (explain each verse) and the no-allusion rule in prompt v2.

The deterministic tests check the prompt text. The live test sends the fixture case to the real LLM
and is skipped unless VYOM_LIVE_LLM=1 (it costs one Groq call):
    $env:VYOM_LIVE_LLM="1"; .\\venv\\python.exe -m pytest backend/tests/test_answer_structure_prompt.py
"""

import json
import os
import re
from pathlib import Path

import pytest

from retrieval.prompt_v2 import LENGTH_REMINDER, SYSTEM_PROMPT_V2, build_rag_prompt_v2

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "allusion_2_14.json").read_text(encoding="utf-8"))
VERSES_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "verses.jsonl"


def _verses(ids: list[str]) -> list[dict]:
    wanted, found = set(ids), {}
    with open(VERSES_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r["verse_id"] in wanted:
                    found[r["verse_id"]] = {**r, "for_question": [0]}
    return [found[i] for i in ids]


def test_system_prompt_asks_for_quote_then_context_meaning_application():
    assert "9. Quote First, Then Explain Each Verse You Use:" in SYSTEM_PROMPT_V2
    # the key-phrase quote must be long enough for the verifier, which only checks quotes of 5+ words
    assert "at least 6 consecutive words copied exactly" in SYSTEM_PROMPT_V2
    assert "Use exactly one quote per verse you explain" in SYSTEM_PROMPT_V2
    assert "who speaks and to whom" in SYSTEM_PROMPT_V2
    assert "what the verse means, in plain everyday words" in SYSTEM_PROMPT_V2
    assert "how it applies to the user's own situation" in SYSTEM_PROMPT_V2
    assert "about 200 words for a single question" in SYSTEM_PROMPT_V2
    # the old cap that kept answers from explaining anything is gone
    assert "at most 3 sentences of commentary" not in SYSTEM_PROMPT_V2
    assert "add at most one plain sentence" not in SYSTEM_PROMPT_V2


def test_system_prompt_forbids_allusions_to_verses_not_shown():
    assert "Never mention, paraphrase or allude to a teaching, image or idea from any other part of the Gita" in SYSTEM_PROMPT_V2
    assert "even without quoting or citing it" in SYSTEM_PROMPT_V2


def test_fixture_prompt_shows_only_the_retrieved_verse():
    prompt = build_rag_prompt_v2(FIXTURE["query"], [FIXTURE["query"]], _verses(FIXTURE["shown_verses"]))
    assert "=== Bhagavad Gita Verse 11.49 ===" in prompt
    assert f"Verse {FIXTURE['absent_verse']} " not in prompt
    absent_text = _verses([FIXTURE["absent_verse"]])[0]["translations"]["english"][0]["text"]
    assert absent_text not in prompt
    assert prompt.rstrip().endswith(LENGTH_REMINDER)


@pytest.mark.skipif(os.getenv("VYOM_LIVE_LLM") != "1", reason="live LLM call; set VYOM_LIVE_LLM=1")
def test_live_answer_does_not_allude_to_absent_verse():
    from llm.client import generate_answer

    prompt = build_rag_prompt_v2(FIXTURE["query"], [FIXTURE["query"]], _verses(FIXTURE["shown_verses"]))
    answer = str(generate_answer(prompt, system_prompt=SYSTEM_PROMPT_V2))
    lowered = answer.lower()
    hits = [p for p in FIXTURE["forbidden_phrases"] if p in lowered]
    assert not hits, f"answer alludes to BG {FIXTURE['absent_verse']}: {hits}\n{answer}"
    cited = set(re.findall(r"BG\s*(\d{1,2}\.\d{1,2})", answer))
    assert cited <= set(FIXTURE["shown_verses"]), f"cites verses not shown: {cited}"
