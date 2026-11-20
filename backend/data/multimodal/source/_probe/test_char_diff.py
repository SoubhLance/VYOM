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


all_diffs = collections.defaultdict(list)
char_counts = collections.Counter()

for ch in range(1, 19):
  ch_path = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
  with open(ch_path, encoding='utf-8') as f:
    verses = json.load(f)

  for v in verses:
    vn = v['verse_number']
    raw = v['text']
    lines = clean_verse_lines(raw)
    norm = ''.join(lines)

    # Let's inspect what is in raw that was removed
    # Expected removals:
    # 1. '\u093c'
    # 2. speaker pattern (if present)
    # 3. trailing marker: [।|॥]+\s*\d+\.\d+\s*[।|॥]+\s*$
    # 4. dandas: । (U+0964), ॥ (U+0965), |
    # 5. whitespace: \s (spaces, \n, \r, \t, etc.)
    # 6. verse markers: digits, '.'

    # Let's simulate removing ONLY the allowed categories from raw, and see what remains:
    # Allowed categories:
    # - U+093C
    # - speaker labels
    # - danda / double danda (U+0964, U+0965, |)
    # - verse-number markers (digits, ., etc. in the trailing marker or verse marker)
    # - whitespace (spaces, newlines, tabs)

    # Let's do a char-by-char multiset or set comparison
    # Let's check raw characters vs normalized characters
    raw_counter = collections.Counter(raw)
    norm_counter = collections.Counter(norm)

    # subtract norm from raw
    diff_counter = raw_counter - norm_counter

    # Remove allowed characters from diff_counter
    # 1. U+093C
    if '\u093c' in diff_counter:
      del diff_counter['\u093c']

    # 2. Whitespace
    for c in list(diff_counter.keys()):
      if c.isspace():
        del diff_counter[c]

    # 3. Dandas: '।', '॥', '|'
    for c in ['।', '॥', '|']:
      if c in diff_counter:
        del diff_counter[c]

    # 4. Speaker labels: characters from speaker patterns that occurred in the text
    # Let's see which speaker pattern matched
    for sp in speaker_patterns:
      if sp in raw:
        # subtract sp chars from diff
        sp_c = collections.Counter(sp)
        for sc, sc_count in sp_c.items():
          if sc in diff_counter:
            diff_counter[sc] -= sc_count
            if diff_counter[sc] <= 0:
              del diff_counter[sc]
        break  # only one speaker pattern per verse

    # 5. Trailing verse marker: e.g. digits, dots
    # Let's find the trailing marker
    m = re.search(r'[।|॥]+\s*(\d+\.\d+)\s*[।|॥]+\s*$', raw.strip())
    if m:
      marker_str = m.group(1)  # e.g. "4.29"
      marker_c = collections.Counter(marker_str)
      for mc, mc_count in marker_c.items():
        if mc in diff_counter:
          diff_counter[mc] -= mc_count
          if diff_counter[mc] <= 0:
            del diff_counter[mc]

    # Now what remains in diff_counter?
    for c, cnt in diff_counter.items():
      char_counts[c] += cnt
      all_diffs[c].append((ch, vn, cnt))

print(f'Remaining missing characters: {dict(char_counts)}')
for c, cnt in char_counts.items():
  print(f'Char {repr(c)} (U+{ord(c):04X}): count {cnt}')
  print(f'  First 10 verses: {all_diffs[c][:10]}')

