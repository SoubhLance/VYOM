import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata = r"backend\data\multimodal\source\_audit"

for sl in ['slide020.png', 'slide021.png', 'slide022.png', 'slide023.png']:
    p = f'backend/data/multimodal/source/_audit/frames/ch01/{sl}'
    res = subprocess.run(
        [tess, p, 'stdout', '-l', 'san', '--tessdata-dir', tessdata, '--psm', '6'],
        capture_output=True, text=True, encoding='utf-8'
    )
    print(f"=== {sl} OCR ===")
    print(res.stdout.strip())
    print()

