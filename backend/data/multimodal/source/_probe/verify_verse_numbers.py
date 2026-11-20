import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

for ch in range(1, 19):
    with open(f"backend/data/gita/{ch}/verses.json", "r", encoding="utf-8") as f:
        v_data = json.load(f)
    v_nums = [row["verse_number"] for row in v_data]
    expected = list(range(1, len(v_nums) + 1))
    assert v_nums == expected, f"Mismatch in ch {ch}: {v_nums} vs {expected}"

print("All 18 chapters have verses strictly 1..N with no gaps.")

