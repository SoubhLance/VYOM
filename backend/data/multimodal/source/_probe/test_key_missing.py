import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
ROOT = Path("backend").resolve()
sys.path.insert(0, str(ROOT))

from llm.client import generate_answer, DEAD_PROVIDERS

DEAD_PROVIDERS.clear()
os.environ["LLM_PROVIDERS"] = "mistral,groq"
if "MISTRAL_API_KEY" in os.environ:
    del os.environ["MISTRAL_API_KEY"]

print("Testing with MISTRAL_API_KEY unset:")
ans = generate_answer("Reply with the single word: ok")
print("Answer:", repr(ans))

