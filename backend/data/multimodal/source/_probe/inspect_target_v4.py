import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(
    'backend/data/multimodal/source/vyom_clips_v4.json', encoding='utf-8'
) as f:
  v4 = json.load(f)

v4_by_id = {c['clip_id']: c for c in v4}

for t in ['bg_01_21', 'bg_01_22']:
  print(f'=== {t} ===')
  print(json.dumps(v4_by_id[t], ensure_ascii=False, indent=2))

