import csv
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(
    'backend/data/multimodal/source/_audit/alignment_report.csv',
    encoding='utf-8',
) as f:
  reader = csv.DictReader(f)
  print('alignment_report fieldnames:', reader.fieldnames)
  for i, row in enumerate(reader):
    if i < 3:
      print(row)

with open(
    'backend/data/multimodal/source/_audit/ocr_blind.csv', encoding='utf-8'
) as f:
  reader = csv.DictReader(f)
  print('\nocr_blind fieldnames:', reader.fieldnames)
  for i, row in enumerate(reader):
    if i < 3:
      print(row)

