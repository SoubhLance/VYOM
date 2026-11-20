import json
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load v4
with open(
    'backend/data/multimodal/source/vyom_clips_v4.json', encoding='utf-8'
) as f:
  v4 = json.load(f)

# Recompute partial for v5
v5 = []
for c in v4:
  c5 = dict(c)
  # All lines of the data verses in text, in order
  all_verse_lines = []
  for tv in c5['text']:
    all_verse_lines.extend(tv['lines'])
  c5['partial'] = c5['spoken_lines'] != all_verse_lines
  v5.append(c5)

partials = [c['clip_id'] for c in v5 if c['partial']]
print(f'Total partial clips in v5: {len(partials)}')
print('Partial clips:')
print(partials)

# Integrity check per chapter
print('\n=== INTEGRITY CHECK PER CHAPTER ===')
pass_count = 0
for ch in range(1, 19):
  ch_clips = [c for c in v5 if c['chapter'] == ch]
  ch_clips.sort(key=lambda x: x['slide'])

  spoken_concat = []
  for c in ch_clips:
    spoken_concat.extend(c['spoken_lines'])

  # Collect normalized verse lines from gita_verses
  # Using the normalized lines stored in data verses text
  # We know the data verses for the chapter
  # Let's get them from backend/data/gita/<ch>/verses.json
  ch_path = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
  with open(ch_path, encoding='utf-8') as f:
    verses_raw = json.load(f)

  # Each verse's normalized line as found in clips
  # Map vn -> lines from the clips
  vn_to_lines = {}
  for c in ch_clips:
    for tv in c['text']:
      vn_to_lines[tv['verse']] = tv['lines']

  # Build expected chapter lines in verse order
  expected_lines = []
  for vn in sorted(vn_to_lines.keys()):
    expected_lines.extend(vn_to_lines[vn])

  if spoken_concat == expected_lines:
    print(
        f'Chapter {ch:2d}: PASS ({len(spoken_concat)} lines, {len(ch_clips)}'
        ' clips)'
    )
    pass_count += 1
  else:
    print(
        f'Chapter {ch:2d}: FAIL ({len(spoken_concat)} spoken vs'
        f' {len(expected_lines)} expected)'
    )
    # Find first differing index
    diff_idx = None
    for idx in range(min(len(spoken_concat), len(expected_lines))):
      if spoken_concat[idx] != expected_lines[idx]:
        diff_idx = idx
        break
    if diff_idx is not None:
      print(f'   First diff at line index {diff_idx}:')
      print(f'      Spoken:   {spoken_concat[diff_idx]}')
      print(f'      Expected: {expected_lines[diff_idx]}')

print(f'\nTotal chapters passing: {pass_count} / 18')

