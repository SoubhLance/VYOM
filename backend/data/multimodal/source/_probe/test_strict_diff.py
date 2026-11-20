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


removed_chars_all = collections.Counter()
unaccounted_all = collections.Counter()
unaccounted_examples = collections.defaultdict(list)

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

    # All characters removed during normalization for this verse:
    removed = raw_c - norm_c
    removed_chars_all.update(removed)

    # Let's identify the source of each removed character:
    # 1. Nukta U+093C
    # 2. Speaker label
    # 3. Trailing marker
    # 4. Whitespace
    # 5. Dandas

    # Reconstruct what should have been removed:
    expected_removed = collections.Counter()

    # Nukta
    if '\u093c' in raw:
      expected_removed['\u093c'] += raw.count('\u093c')

    # Speaker
    for sp in speaker_patterns:
      if sp in raw:
        expected_removed.update(collections.Counter(sp))
        break

    # Trailing marker
    m = re.search(r'([।|॥]+\s*\d+\.\d+\s*[।|॥]+\s*)$', raw.strip())
    if m:
      expected_removed.update(collections.Counter(m.group(1)))

    # Whitespace and dandas anywhere in raw that are not in normalized lines
    for char, cnt in removed.items():
      if char.isspace() or char in ['।', '॥', '|']:
        # these are whitespace / danda
        pass
      elif char == '\u093c':
        pass
      else:
        # Check if accounted for by speaker or trailing marker
        exp_cnt = expected_removed.get(char, 0)
        if cnt > exp_cnt:
          diff = cnt - exp_cnt
          unaccounted_all[char] += diff
          unaccounted_examples[char].append((ch, vn, raw))

print('Total characters removed across all 701 verses:')
for c, cnt in removed_chars_all.most_common():
  print(f'  {repr(c)} (U+{ord(c):04X}): {cnt}')

print('\nUnaccounted missing characters:')
print(dict(unaccounted_all))

