import csv
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

matches = [
    r
    for r in csv.DictReader(
        open(
            'backend/data/multimodal/source/_audit/alignment_report.csv',
            encoding='utf-8',
        )
    )
    if r['class'] == 'MATCH'
]
matches.sort(key=lambda x: float(x['similarity_score']))
ocr_by_cs = {
    (int(r['chapter']), int(r['slide'])): r
    for r in csv.DictReader(
        open(
            'backend/data/multimodal/source/_audit/ocr_blind.csv',
            encoding='utf-8',
        )
    )
}
clips_v3 = {
    (c['chapter'], c['slide']): c
    for c in json.load(
        open(
            'backend/data/multimodal/source/vyom_clips_v3.json',
            encoding='utf-8',
        )
    )
}

for idx in range(8, 18):
  r = matches[idx]
  ch, sl, sc = int(r['chapter']), int(r['slide']), float(r['similarity_score'])
  ocr = ocr_by_cs.get((ch, sl), {})
  clip = clips_v3.get((ch, sl), {})
  ocr_parts = []
  if ocr.get('speaker_label'):
    ocr_parts.append(f"[{ocr['speaker_label'].strip()}]")
  for lk in ['line1', 'line2', 'line3']:
    val = ocr.get(lk, '').strip()
    if val:
      ocr_parts.append(val)
  print(f'### {idx+1}. Chapter {ch}, Slide {sl} (Score: {sc:.3f})')
  print(f"- **OCR Text:** {' // '.join(ocr_parts)}")
  print('- **Spoken Lines (v3):**')
  for l in clip.get('spoken_lines', []):
    print(f"  - `{l.replace(chr(10), ' ')}`")
  print()

