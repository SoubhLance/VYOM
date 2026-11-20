import sys
from pathlib import Path

ROOT = Path("backend").resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "retrieval"))

from verify_quotes import check_quotes, normalize_text, extract_quotes

print("Import successful!")
sample = 'Krishna says "The soul is neither born, nor does it ever die; nor having once existed, does it ever cease to be" and also "a short quote".'
quotes = extract_quotes(sample)
print("Extracted quotes (>=6 words):", quotes)
res = check_quotes(sample, [{"translations": {"english": [{"text": "The soul is neither born, nor does it ever die; nor having once existed, does it ever cease to be."}]}}])
print("Result:", res)
assert len(res["verified"]) == 1
assert len(res["unverified"]) == 0
print("Unit test passed!")

