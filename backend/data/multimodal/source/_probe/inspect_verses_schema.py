import collections
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

key_counts = collections.Counter()
total_objects = 0
samples = {}

for ch in range(1, 19):
  p = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
  if not p.exists():
    p = pathlib.Path(f'backend/data/gita/{ch:02d}/verses.json')
  with open(p, encoding='utf-8') as f:
    verses = json.load(f)
  for v in verses:
    total_objects += 1
    for k in v.keys():
      key_counts[k] += 1
    if ch == 2 and v.get('verse_number') == 47:
      samples['2.47'] = v
    if ch == 1 and v.get('verse_number') == 1:
      samples['1.1'] = v

print(f'Total verse objects across all chapters: {total_objects}')
print('\nKey counts (union across all chapters):')
for k, count in key_counts.most_common():
  print(f'  {k}: {count} / {total_objects}')

print('\n=== Sample Raw Object: 1.1 ===')
print(json.dumps(samples.get('1.1'), ensure_ascii=False, indent=2))

print('\n=== Sample Raw Object: 2.47 ===')
print(json.dumps(samples.get('2.47'), ensure_ascii=False, indent=2))

