import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(
    'backend/data/multimodal/source/vyom_clips_v2.json', encoding='utf-8'
) as f:
  v2 = json.load(f)

with open(
    'backend/data/multimodal/source/vyom_clips_v3.json', encoding='utf-8'
) as f:
  v3 = json.load(f)

print(f'Total v3 entries: {len(v3)}')

v2_by_id = {c['clip_id']: c for c in v2}
v3_by_id = {c['clip_id']: c for c in v3}

changes = []
for cid, c3 in v3_by_id.items():
  c2 = v2_by_id[cid]
  # Compare existing v2 fields
  diff_fields = []
  for k in c2.keys():
    if c2[k] != c3.get(k):
      diff_fields.append(k)
  if diff_fields:
    changes.append((cid, diff_fields))

print(f'\nTotal entries changed vs v2 (ignoring new text_raw field): {len(changes)}')
for cid, fields in changes:
  print(f'  {cid}: changed fields = {fields}')
  for fld in fields:
    print(f'     v2 {fld}: {v2_by_id[cid][fld]}')
    print(f'     v3 {fld}: {v3_by_id[cid][fld]}')

print('\n=== Target entries (speaker, spoken_lines only) ===')
for target in ['bg_01_27', 'bg_04_29']:
  entry = v3_by_id[target]
  filtered = {
      'clip_id': entry['clip_id'],
      'speaker': entry['speaker'],
      'spoken_lines': entry['spoken_lines'],
  }
  print(f'\n--- {target} ---')
  print(json.dumps(filtered, ensure_ascii=False, indent=2))

