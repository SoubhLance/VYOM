import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

targets = [
    (1, [20, 21, 22, 23]),
    (4, [24, 25, 26]),
    (6, [22, 23, 24, 25])
]

for ch, verses in targets:
    path = f'backend/data/gita/{ch}/verses.json'
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    v_by_num = {v['verse_number']: v for v in data}
    for vn in verses:
        v = v_by_num.get(vn)
        print(f"=== Chapter {ch}, Verse {vn} ===")
        if v:
            print("--- repr ---")
            print(repr(v['text']))
            print("--- text ---")
            print(v['text'])
        else:
            print("NOT FOUND")
        print()

