import csv
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
out_csv = S / 'slide_map_v2.csv'

# Verse counts per chapter:
# 47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78
# Slide counts per chapter: same as verse counts, except ch1 has 46 slides!
slide_counts = {
    1: 46,
    2: 72,
    3: 43,
    4: 42,
    5: 29,
    6: 47,
    7: 30,
    8: 28,
    9: 34,
    10: 42,
    11: 55,
    12: 20,
    13: 35,
    14: 27,
    15: 20,
    16: 24,
    17: 28,
    18: 78,
}

rows = []
for ch in range(1, 19):
  n_slides = slide_counts[ch]
  for sl in range(1, n_slides + 1):
    # Determine data_verses for this slide
    if ch == 1:
      if sl < 20:
        dv = str(sl)
      elif sl == 20:
        dv = '20;21'
      elif sl == 21:
        dv = '21;22'
      elif sl == 22:
        dv = '22'
      elif 23 <= sl <= 25:
        dv = str(sl)
      elif 26 <= sl <= 36:
        dv = f'{sl};{sl+1}'
      elif 37 <= sl <= 46:
        dv = str(sl + 1)
    elif ch == 4:
      if sl < 29:
        dv = str(sl)
      elif sl == 29:
        dv = '29;30'
      elif sl == 30:
        dv = '30;31'
      elif sl == 31:
        dv = '31'
      else:
        dv = str(sl)
    elif ch == 6:
      if sl < 23:
        dv = str(sl)
      elif sl == 23:
        dv = '23'
      elif sl == 24:
        dv = '23;24'
      else:
        dv = str(sl)
    else:
      dv = str(sl)

    rows.append({'chapter': ch, 'slide': sl, 'data_verses': dv})

assert len(rows) == 700, f'Expected 700 rows, got {len(rows)}'

with open(out_csv, 'w', encoding='utf-8', newline='') as f:
  writer = csv.DictWriter(f, fieldnames=['chapter', 'slide', 'data_verses'])
  writer.writeheader()
  writer.writerows(rows)

print(f'Wrote {out_csv} with {len(rows)} rows.')

