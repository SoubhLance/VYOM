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

# Load v3 clips
with open(
    'backend/data/multimodal/source/vyom_clips_v3.json', encoding='utf-8'
) as f:
  clips_v3 = json.load(f)
clips_by_cs = {(c['chapter'], c['slide']): c for c in clips_v3}

for idx, r in enumerate(lowest_25, 1):
  ch = int(r['chapter'])
  sl = int(r['slide'])
  sc = float(r['similarity_score'])
  ocr = ocr_by_cs.get((ch, sl), {})
  clip = clips_by_cs.get((ch, sl), {})

  ocr_parts = []
  if ocr.get('speaker_label'):
    ocr_parts.append(f"[{ocr['speaker_label'].strip()}]")
  for lk in ['line1', 'line2', 'line3']:
    val = ocr.get(lk, '').strip()
    if val:
      ocr_parts.append(val)
  ocr_text = ' // '.join(ocr_parts) if ocr_parts else '(empty OCR)'
  sp_lines = clip.get('spoken_lines', [])

  print(f'### {idx}. Chapter {ch}, Slide {sl} (Score: {sc:.3f})')
  print(f'- **OCR Text:** {ocr_text}')
  print(f'- **Spoken Lines (v3):**')
  for l in sp_lines:
    # clean any newlines within the line for compact display
    l_display = l.replace('\n\n', ' | ').replace('\n', ' ')
    print(f'  - `{l_display}`')
  print()

