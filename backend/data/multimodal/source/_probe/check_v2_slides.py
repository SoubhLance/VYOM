import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(
    'backend/data/multimodal/source/vyom_clips_v2.json', encoding='utf-8'
) as f:
  clips = json.load(f)

for c in clips:
  if c['chapter'] == 1 and c['slide'] in [33, 34]:
    print(f"=== Slide {c['slide']} ===")
    print('data_verses:', c['data_verses'])
    for t in c['text']:
      print(f"  text verse {t['verse']}: {t['lines']}")
    print('spoken_lines:', c['spoken_lines'])

for c in clips:
  if c['chapter'] == 4 and c['slide'] in [28, 29, 30]:
    print(f"=== Slide {c['slide']} ===")
    print('data_verses:', c['data_verses'])
    for t in c['text']:
      print(f"  text verse {t['verse']}: {t['lines']}")
    print('spoken_lines:', c['spoken_lines'])

