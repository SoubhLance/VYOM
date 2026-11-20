import httpx
from groq import APIStatusError
from google.api_core.exceptions import NotFound

def _extract_status_code(e: Exception) -> int | None:
    if hasattr(e, "status_code") and isinstance(e.status_code, int):
        return e.status_code
    if hasattr(e, "response") and hasattr(e.response, "status_code"):
        return e.response.status_code
    if hasattr(e, "code") and isinstance(e.code, int):
        return e.code
    import re
    m = re.search(r'\b(40[0-9]|4[1-9][0-9]|5[0-9]{2})\b', str(e))
    if m:
        return int(m.group(1))
    return None

# Test with httpx HTTPStatusError
req = httpx.Request("POST", "https://api.mistral.ai/v1/chat/completions")
resp = httpx.Response(401, request=req)
err1 = httpx.HTTPStatusError("401 Client Error", request=req, response=resp)
print("httpx 401:", _extract_status_code(err1))

# Test with google NotFound
err2 = NotFound("404 Not Found")
print("google 404:", _extract_status_code(err2))

# Test with Timeout
err3 = httpx.ReadTimeout("timed out")
print("timeout:", _extract_status_code(err3))

