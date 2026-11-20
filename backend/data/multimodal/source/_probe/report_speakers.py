import collections
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Distinct variants found in verses.json
variants = collections.Counter()
variant_verses = collections.defaultdict(list)
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
    matches = speaker_regex.findall(raw)
    for m in matches:
      variants[m] += 1
      variant_verses[m].append(f'{ch}.{vn}')

print('=== SPEAKER VARIANTS IN ALL VERSES.JSON ===')
for s, cnt in variants.most_common():
  print(f'  {repr(s)}: count={cnt}')
print(f'Total occurrences: {sum(variants.values())}')

# In vyom_clips_v4.json, count of clips with each canonical speaker:
with open(
    'backend/data/multimodal/source/vyom_clips_v4.json', encoding='utf-8'
) as f:
  v4 = json.load(f)

v4_spk = collections.Counter(c['speaker'] for c in v4 if c['speaker'])
print('\n=== CANONICAL SPEAKERS IN VYOM_CLIPS_V4.JSON ===')
for spk, cnt in v4_spk.most_common():
  print(f'  {repr(spk)}: count={cnt}')
print(f'Total clips with speaker: {sum(v4_spk.values())}')

