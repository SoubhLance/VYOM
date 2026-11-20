import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv("backend/.env")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

try:
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "hi"}]
    )
    print("Success with model:", completion.model)
except Exception as e:
    print("llama-3.3-70b-versatile failed with:", type(e).__name__)
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "hi"}]
    )
    print("Fallback succeeded with model:", completion.model)

