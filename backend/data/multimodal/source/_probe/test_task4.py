import csv
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load alignment_report.csv
matches = []
with open(
    'backend/data/multimodal/source/_audit/alignment_report.csv',
    encoding='utf-8',
) as f:
  for r in csv.DictReader(f):
    if r['class'] == 'MATCH':
      matches.append(r)

matches.sort(key=lambda x: float(x['similarity_score']))
lowest_25 = matches[:25]

# Load ocr_blind.csv
ocr_by_cs = {}
with open(
    'backend/data/multimodal/source/_audit/ocr_blind.csv', encoding='utf-8'
) as f:
  for r in csv.DictReader(f):
    ocr_by_cs[(int(r['chapter']), int(r['slide']))] = r

# Load v2 clips (to test spoken_lines)
with open(
    'backend/data/multimodal/source/vyom_clips_v2.json', encoding='utf-8'
) as f:
  clips_v2 = json.load(f)
clips_by_cs = {(c['chapter'], c['slide']): c for c in clips_v2}

for idx, r in enumerate(lowest_25, 1):
  ch = int(r['chapter'])
  sl = int(r['slide'])
  sc = float(r['similarity_score'])
  ocr = ocr_by_cs.get((ch, sl), {})
  clip = clips_by_cs.get((ch, sl), {})

  ocr_lines = [
      ocr.get('line1', ''),
      ocr.get('line2', ''),
      ocr.get('line3', ''),
  ]
  ocr_text = ' / '.join([l.strip() for l in ocr_lines if l.strip()])
  sp_lines = clip.get('spoken_lines', [])

  print(f'{idx:2d}. Ch {ch:2d} Slide {sl:2d} | Score: {sc:.3f}')
  print(f'    OCR:    {ocr_text}')
  print(f'    Spoken: {sp_lines}')

