import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(
    'backend/data/multimodal/source/vyom_clips_v3.json', encoding='utf-8'
) as f:
  v3 = json.load(f)

with open(
    'backend/data/multimodal/source/vyom_clips_v4.json', encoding='utf-8'
) as f:
  v4 = json.load(f)

print(f'Total v4 entries: {len(v4)}')

v3_by_id = {c['clip_id']: c for c in v3}
v4_by_id = {c['clip_id']: c for c in v4}

# Check diffs against v3
# All v4 entries have the new field search_text.
# Let's list diffs per entry for existing fields, and also note search_text
diffs = []
for cid, c4 in v4_by_id.items():
  c3 = v3_by_id[cid]
  changed_fields = []
  for k in c3.keys():
    if c3[k] != c4.get(k):
      changed_fields.append(k)
  if 'search_text' in c4 and 'search_text' not in c3:
    pass  # globally added
  if changed_fields:
    diffs.append((cid, changed_fields))

print(
    f'\nEntries with differences in existing fields vs v3 (excluding new'
    f' search_text): {len(diffs)}'
)
for cid, flds in diffs:
  print(f'  {cid}: {flds}')

# Print full v4 entries for bg_01_20, bg_01_21, bg_01_22, bg_01_24, bg_06_23, bg_06_24
targets = [
    'bg_01_20',
    'bg_01_21',
    'bg_01_22',
    'bg_01_24',
    'bg_06_23',
    'bg_06_24',
]
print('\n=== FULL V4 ENTRIES ===')
for t in targets:
  print(f'\n--- {t} ---')
  print(json.dumps(v4_by_id[t], ensure_ascii=False, indent=2))

