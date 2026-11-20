import json
from pathlib import Path

path = Path("backend/data/processed/verses.jsonl")
with open(path, "r", encoding="utf-8") as f:
    sample = json.loads(f.readline())

print("verses.jsonl keys:", list(sample.keys()))
if "translations" in sample:
    print("translations type:", type(sample["translations"]))
    if isinstance(sample["translations"], dict):
        print("translations sub-keys:", list(sample["translations"].keys()))
        eng = sample["translations"].get("english", [])
        print(f"english translations count: {len(eng)}")
        if eng:
            print("first item keys:", list(eng[0].keys()))
            print("first item author:", eng[0].get("author"))

raw_ch1 = Path("backend/data/gita/01/verses.json")
if raw_ch1.exists():
    with open(raw_ch1, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list) and data:
            print("raw gita 01 verse keys:", list(data[0].keys()))
        elif isinstance(data, dict):
            first_v = next(iter(data.values()))
            print("raw gita 01 verse keys:", list(first_v.keys()))

