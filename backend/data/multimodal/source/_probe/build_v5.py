import json
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
v4_path = S / 'vyom_clips_v4.json'
v5_path = S / 'vyom_clips_v5.json'

with open(v4_path, encoding='utf-8') as f:
  v4 = json.load(f)

v5 = []
partial_changed = []

for c in v4:
  c5 = dict(c)
  # all lines of the data verses in text, in order
  all_verse_lines = []
  for tv in c5['text']:
    all_verse_lines.extend(tv['lines'])

  # recompute partial
  new_partial = c5['spoken_lines'] != all_verse_lines
  if new_partial != c5['partial']:
    partial_changed.append(
        (c5['clip_id'], f"v4={c5['partial']} -> v5={new_partial}")
    )
  c5['partial'] = new_partial
  v5.append(c5)

with open(v5_path, 'w', encoding='utf-8') as f:
  json.dump(v5, f, ensure_ascii=False, indent=2)

print(f'Wrote {v5_path} with {len(v5)} entries.')
print(f'Clips where partial changed vs v4: {len(partial_changed)}')
for cid, chg in partial_changed:
  print(f'  {cid}: {chg}')

