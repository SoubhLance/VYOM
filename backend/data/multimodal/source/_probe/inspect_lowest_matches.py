import csv
import sys

sys.stdout.reconfigure(encoding='utf-8')

matches = []
with open(
    'backend/data/multimodal/source/_audit/alignment_report.csv',
    encoding='utf-8',
) as f:
  for r in csv.DictReader(f):
    if r['class'] == 'MATCH':
      matches.append(r)

print(f'Total MATCH rows: {len(matches)}')
matches.sort(key=lambda x: float(x['similarity_score']))

print('Lowest 25 MATCH rows:')
for r in matches[:25]:
  print(
      f"Ch {r['chapter']} Slide {r['slide']} (score {r['similarity_score']}):"
      f" match={r['data_verse_match']}"
  )

