import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('backend/data/gita/1/verses.json', encoding='utf-8') as f:
  verses = json.load(f)
v34 = next(v for v in verses if v['verse_number'] == 34)
print('v34:', repr(v34['text']))

