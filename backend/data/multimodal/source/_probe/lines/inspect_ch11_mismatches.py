import json
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata = r"backend\data\multimodal\source\_audit"

for ch, sl in [
    (11, 29),
    (11, 32),
    (11, 33),
    (11, 34),
    (11, 38),
    (11, 43),
    (11, 49),
    (15, 3),
]:
  p = f'backend/data/multimodal/source/_audit/frames/ch{ch:02d}/slide{sl:03d}.png'
  res = subprocess.run(
      [
          tess,
          p,
          'stdout',
          '-l',
          'san',
          '--tessdata-dir',
          tessdata,
          '--psm',
          '6',
      ],
      capture_output=True,
      text=True,
      encoding='utf-8',
  )
  print(f'=== Ch {ch} Slide {sl} ===')
  print('OCR:')
  print(res.stdout.strip())
  print()

