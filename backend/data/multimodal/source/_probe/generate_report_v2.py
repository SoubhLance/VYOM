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
    'धृतराष्ट्र उवाच',
]


def clean_verse_lines(raw_text):
  t = raw_text.replace('\u093c', '')
  for sp in speaker_patterns:
    if sp in t:
      t = t.replace(sp, '')
  t = re.sub(r'[।|॥]+\s*\d+\.\d+\s*[।|॥]+\s*$', '', t.strip())
  parts = t.split('।')
  lines = [p.strip() for p in parts if p.strip()]
  return lines


# 2. Raw vs normalized diff over all verses
missing_other = collections.Counter()
missing_refs = collections.defaultdict(list)

# Excluded categories:
# - U+093C
# - speaker label
# - danda / double danda: । (U+0964), ॥ (U+0965), |
# - verse-number markers: trailing [।|॥]+\s*\d+\.\d+\s*[।|॥]+
# - whitespace: \s (spaces, \n, \r, \t, etc.)

for ch in range(1, 19):
  ch_path = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
  with open(ch_path, encoding='utf-8') as f:
    verses = json.load(f)

  for v in verses:
    vn = v['verse_number']
    raw = v['text']
    lines = clean_verse_lines(raw)

    raw_c = collections.Counter(raw)
    norm_c = collections.Counter(''.join(lines))
    diff_c = raw_c - norm_c

    # subtract U+093C
    if '\u093c' in diff_c:
      del diff_c['\u093c']

    # subtract whitespace
    for c in list(diff_c.keys()):
      if c.isspace():
        del diff_c[c]

    # subtract dandas
    for c in ['।', '॥', '|']:
      if c in diff_c:
        del diff_c[c]

    # subtract speaker label
    for sp in speaker_patterns:
      if sp in raw:
        for sc, sc_cnt in collections.Counter(sp).items():
          if sc in diff_c:
            diff_c[sc] -= sc_cnt
            if diff_c[sc] <= 0:
              del diff_c[sc]
        break

    # subtract trailing verse marker
    m = re.search(r'[।|॥]+\s*(\d+\.\d+)\s*[।|॥]+\s*$', raw.strip())
    if m:
      marker_str = m.group(1)
      for mc, mc_cnt in collections.Counter(marker_str).items():
        if mc in diff_c:
          diff_c[mc] -= mc_cnt
          if diff_c[mc] <= 0:
            del diff_c[mc]

    # Any remaining character
    for c, cnt in diff_c.items():
      missing_other[c] += cnt
      missing_refs[c].append(f'BG {ch}.{vn}')

print('=== 2. RAW VS NORMALIZED DIFF OVER ALL VERSES ===')
print(
    f'Characters missing other than excluded categories: {len(missing_other)}'
)
if missing_other:
  for c, cnt in missing_other.items():
    print(f"Char '{c}' (U+{ord(c):04X}): count {cnt}")
    print(f'  First 10 verse references: {missing_refs[c][:10]}')
else:
  print('None. Count per character: 0 for all non-excluded characters.')

# 4.29 line 1 comparison
v4_29 = next(
    v
    for v in json.load(open('backend/data/gita/4/verses.json', encoding='utf-8'))
    if v['verse_number'] == 29
)
raw_4_29_l1 = v4_29['text'].split('।')[0].strip()
norm_4_29_l1 = clean_verse_lines(v4_29['text'])[0]

print('\nCh 4.29 Line 1:')
print(f'Raw:        {raw_4_29_l1}')
print(f'Normalized: {norm_4_29_l1}')
print(f'Identical:  {raw_4_29_l1 == norm_4_29_l1}')
print(
    'Raw repr:  ',
    repr(raw_4_29_l1),
    'Codepoints:',
    [f'U+{ord(c):04X}' for c in raw_4_29_l1],
)
print(
    'Norm repr: ',
    repr(norm_4_29_l1),
    'Codepoints:',
    [f'U+{ord(c):04X}' for c in norm_4_29_l1],
)

print('\n=== 3. FULL V2 ENTRIES ===')
with open(
    'backend/data/multimodal/source/vyom_clips_v2.json', encoding='utf-8'
) as f:
  v2_clips = json.load(f)

v2_by_id = {c['clip_id']: c for c in v2_clips}
for target in ['bg_01_27', 'bg_01_28', 'bg_04_30', 'bg_01_46']:
  print(f'\n--- {target} ---')
  print(json.dumps(v2_by_id[target], ensure_ascii=False, indent=2))

