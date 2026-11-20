import json
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
v5_path = S / 'vyom_clips_v5.json'

with open(v5_path, encoding='utf-8') as f:
  v5 = json.load(f)

print('=== 5. PARTIAL IS TRUE ENTRIES ===')
partial_clips = [c['clip_id'] for c in v5 if c['partial']]
print(f'Count: {len(partial_clips)}')
for cid in partial_clips:
  print(f'  {cid}')

print('\n=== 4. INTEGRITY CHECK PER CHAPTER ===')
total_passed = 0

for ch in range(1, 19):
  ch_clips = [c for c in v5 if c['chapter'] == ch]
  ch_clips.sort(key=lambda x: x['slide'])

  spoken_concat = []
  slide_of_line = []
  clip_of_line = []
  for c in ch_clips:
    for line in c['spoken_lines']:
      spoken_concat.append(line)
      slide_of_line.append(c['slide'])
      clip_of_line.append(c['clip_id'])

  # Load all verses of chapter from backend/data/gita/<ch>/verses.json
  # To get canonical lines in verse order
  ch_path = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
  with open(ch_path, encoding='utf-8') as f:
    verses_raw = json.load(f)

  # Map verse_number -> text lines from the clips (where corrections and whitespace collapsing have occurred)
  vn_to_lines = {}
  for c in ch_clips:
    for tv in c['text']:
      vn_to_lines[tv['verse']] = tv['lines']

  # Expected lines in verse order
  expected_lines = []
  expected_vn = []
  for vn in sorted(vn_to_lines.keys()):
    for l_idx, line in enumerate(vn_to_lines[vn], 1):
      expected_lines.append(line)
      expected_vn.append(f'{ch}.{vn} L{l_idx}')

  # Check equality
  if spoken_concat == expected_lines:
    print(
        f'Chapter {ch:2d}: PASS ({len(spoken_concat)} lines across'
        f' {len(ch_clips)} slides)'
    )
    total_passed += 1
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
    if diff_idx is None:
      diff_idx = min(len(spoken_concat), len(expected_lines))
    differing_clip = (
        clip_of_line[diff_idx]
        if diff_idx < len(clip_of_line)
        else ch_clips[-1]['clip_id']
    )
    sp_str = (
        spoken_concat[diff_idx] if diff_idx < len(spoken_concat) else '<EOF>'
    )
    exp_str = (
        expected_lines[diff_idx] if diff_idx < len(expected_lines) else '<EOF>'
    )
    print(f'   First differing clip_id: {differing_clip}')
    print(f'   Spoken:   {repr(sp_str)}')
    print(f'   Expected: {repr(exp_str)}')

print(f'\nTotal chapters passing: {total_passed} / 18')

