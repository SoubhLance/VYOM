import httpx

try:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get("https://api.mistral.ai/v1/models", headers={"Authorization": "Bearer invalid_test_key"})
        print("Status code:", resp.status_code)
except Exception as e:
    print("Exception:", type(e).__name__)

