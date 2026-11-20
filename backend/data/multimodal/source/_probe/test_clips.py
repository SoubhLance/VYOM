import json
import sys
from pathlib import Path

# Add backend and backend/api to sys.path
ROOT = Path("backend").resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.stdout.reconfigure(encoding="utf-8")

from clips import clips_for, mount_audio, load_verse_clips
from fastapi import FastAPI
from fastapi.testclient import TestClient

print("--- Testing load_verse_clips() ---")
store = load_verse_clips()
print(f"Loaded store with {len(store)} verses")

print("\n--- Testing clips_for('2.47') ---")
c_2_47 = clips_for("2.47")
print(json.dumps(c_2_47, ensure_ascii=False, indent=2))

print("\n--- Testing clips_for('1.27') ---")
c_1_27 = clips_for("1.27")
print(json.dumps(c_1_27, ensure_ascii=False, indent=2))

print("\n--- Testing throwaway FastAPI app with mount_audio() ---")
app = FastAPI()
mount_audio(app)

client = TestClient(app)

url = "/audio/verses/bg_02_47.mp3"
resp = client.get(url)
print(f"Request URL: {url}")
print(f"HTTP Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('content-type')}")
print(f"Content-Length header: {resp.headers.get('content-length')}")
print(f"Body size: {len(resp.content)} bytes")

# Traversal test
bad_url = "/audio/../../../../etc/passwd"
resp_bad = client.get(bad_url)
print(f"\nTraversal test ({bad_url}) Status: {resp_bad.status_code}")

bad_url2 = "/audio/../lecture.mp4"
resp_bad2 = client.get(bad_url2)
print(f"Traversal test ({bad_url2}) Status: {resp_bad2.status_code}")
