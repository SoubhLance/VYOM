import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata = r"backend\data\multimodal\source\_audit"

for name in ['ch04_slide024_start.png', 'ch04_slide024_end.png', 'ch04_slide025_start.png', 'ch04_slide025_end.png']:
    p = f'backend/data/multimodal/source/_probe/lines/{name}'
    res = subprocess.run(
        [tess, p, 'stdout', '-l', 'san', '--tessdata-dir', tessdata, '--psm', '6'],
        capture_output=True, text=True, encoding='utf-8'
    )
    print(f"=== {name} ===")
    print(res.stdout.strip())
    print()

