import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata = r"backend\data\multimodal\source\_audit"

for p in [
    'backend/data/multimodal/source/_audit/frames/ch13/slide001.png',
    'backend/data/multimodal/source/_audit/frames/ch13/slide002.png',
    'backend/data/multimodal/source/_audit/frames/ch01/slide024.png',
]:
    res = subprocess.run(
        [tess, p, 'stdout', '-l', 'san', '--tessdata-dir', tessdata, '--psm', '6'],
        capture_output=True, text=True, encoding='utf-8'
    )
    print(f"=== {p} OCR ===")
    print(res.stdout.strip())
    print()

