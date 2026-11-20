import json

with open("backend/data/processed/verses.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data["verse_id"] == "16.2":
            eng = data["translations"]["english"]
            for t in eng:
                print(t["author"], ":", repr(t["text"]))

