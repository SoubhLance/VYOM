from pathlib import Path
from dotenv import dotenv_values

env_path = Path("backend/.env")
vals = dotenv_values(env_path)

mistral_key = vals.get("MISTRAL_API_KEY")
gemini_model = vals.get("GEMINI_MODEL")

print("--- Checking backend/.env ---")
if mistral_key:
    masked_key = mistral_key[:4] + "*" * (len(mistral_key) - 4)
    print(f"MISTRAL_API_KEY is SET: {masked_key[:4]}... (length={len(mistral_key)})")
else:
    print("MISTRAL_API_KEY is UNSET")

if gemini_model:
    print(f"GEMINI_MODEL is SET: {gemini_model}")
else:
    print("GEMINI_MODEL is UNSET")

