import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

print("="*60)
print("1. GET /api/health")
print("="*60)
req = urllib.request.Request(f"{BASE_URL}/api/health")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print(f"Status: {resp.status}")
    print(f"Body: {json.dumps(data, indent=2)}")

print("\n" + "="*60)
print("2. POST /api/ask {\"query\": \"1.27\"}")
print("="*60)
req_body = json.dumps({"query": "1.27"}).encode("utf-8")
req = urllib.request.Request(
    f"{BASE_URL}/api/ask",
    data=req_body,
    headers={"Content-Type": "application/json"}
)
audio_url_sample = None
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Status: {resp.status}")
        print(f"routed: {data.get('routed')}")
        print(f"cited_verses: {data.get('cited_verses')}")
        print("sources:")
        for idx, s in enumerate(data.get("sources", []), 1):
            vid = s.get("verse_id")
            is_n = s.get("is_neighbor")
            clips_info = [
                f"{c.get('clip_id')} (partial={c.get('partial')})"
                for c in s.get("clips", [])
            ]
            print(f"  Source {idx}: verse_id={vid}, is_neighbor={is_n}, clips={clips_info}")
            if not audio_url_sample and s.get("clips"):
                audio_url_sample = s["clips"][0].get("audio_url")
        print(f"\nanswer preview: {data.get('answer', '')[:100]}...")
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} - {e.read().decode('utf-8')}")

print("\n" + "="*60)
print("3. POST /api/ask {\"query\": \"action without attachment to results\"}")
print("="*60)
req_body2 = json.dumps({"query": "action without attachment to results"}).encode("utf-8")
req2 = urllib.request.Request(
    f"{BASE_URL}/api/ask",
    data=req_body2,
    headers={"Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req2) as resp:
        data2 = json.loads(resp.read().decode("utf-8"))
        print(f"Status: {resp.status}")
        print(f"routed: {data2.get('routed')}")
        print(f"cited_verses: {data2.get('cited_verses')}")
        print("sources:")
        for idx, s in enumerate(data2.get("sources", []), 1):
            vid = s.get("verse_id")
            clip_ids = [c.get("clip_id") for c in s.get("clips", [])]
            print(f"  Source {idx}: verse_id={vid}, clips={clip_ids}")
            if not audio_url_sample and s.get("clips"):
                audio_url_sample = s["clips"][0].get("audio_url")
        ans = data2.get("answer")
        if ans:
            print(f"Answer text generated successfully! (Length: {len(ans)} chars)")
            print(f"Answer snippet: {ans[:150]}...")
        else:
            print("Answer text was empty.")
except urllib.error.HTTPError as e:
    err_body = e.read().decode("utf-8")
    print(f"HTTPError: {e.code} - {err_body}")

print("\n" + "="*60)
print(f"4. HEAD {audio_url_sample}")
print("="*60)
if audio_url_sample:
    head_req = urllib.request.Request(f"{BASE_URL}{audio_url_sample}", method="HEAD")
    with urllib.request.urlopen(head_req) as resp:
        print(f"Status: {resp.status}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print(f"Content-Length: {resp.headers.get('Content-Length')}")
else:
    print("No audio_url found in responses.")

