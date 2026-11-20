import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('backend/data/gita/1/verses.json', encoding='utf-8') as f:
  v = next(x for x in json.load(f) if x['verse_number'] == 24)
print('Ch 1 Verse 24 in data:')
print(repr(v['text']))

