import collections
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

speaker_patterns = [
    'श्री भगवानुवाच',
    'श्रीभगवानुवाच',
    'भगवानुवाच',
    'अर्जुन उवाच',
    'सञ्जय उवाच',
    'संजय उवाच',
    'धृतराष्ट्र उवाच',
]

variants = collections.Counter()
variant_verses = collections.defaultdict(list)

# Regex to match any speaker pattern anywhere or at start
speaker_regex = re.compile(
    r'(श्री\s*भगवानुवाच|भगवानुवाच|अर्जुन\s*उवाच|सञ्जय\s*उवाच|संजय\s*उवाच|धृतराष्ट्र\s*उवाच)'
)

for ch in range(1, 19):
  p = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
  with open(p, encoding='utf-8') as f:
    verses = json.load(f)
  for v in verses:
    vn = v['verse_number']
    raw = v['text']
    # Search for all matches
    matches = speaker_regex.findall(raw)
    for m in matches:
      variants[m] += 1
      variant_verses[m].append(f'{ch}.{vn}')

print('All speaker label variants found across all verses.json:')
for s, cnt in variants.most_common():
  print(f'  {repr(s)}: count {cnt}, verses={variant_verses[s]}')

print(f'\nTotal occurrences: {sum(variants.values())}')

