import os
from pathlib import Path
from dotenv import load_dotenv

_backend_dir = Path("backend").resolve()
if (_backend_dir / ".env").exists():
    load_dotenv(_backend_dir / ".env")
elif (_backend_dir.parent / ".env").exists():
    load_dotenv(_backend_dir.parent / ".env")

for k in ["GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "MISTRAL_MODEL", "LLM_PROVIDERS"]:
    val = os.getenv(k)
    status = f"SET (len={len(val)})" if val else "UNSET"
    print(f"{k}: {status}")

