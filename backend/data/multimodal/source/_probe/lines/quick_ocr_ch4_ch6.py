import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata = r"backend\data\multimodal\source\_audit"

for ch, slides in [(4, [24, 25, 26]), (6, [22, 23, 24, 25])]:
    for sl in slides:
        p = f'backend/data/multimodal/source/_audit/frames/ch{ch:02d}/slide{sl:03d}.png'
        res = subprocess.run(
            [tess, p, 'stdout', '-l', 'san', '--tessdata-dir', tessdata, '--psm', '6'],
            capture_output=True, text=True, encoding='utf-8'
        )
        print(f"=== Ch {ch} Slide {sl} OCR ===")
        print(res.stdout.strip())
        print()

