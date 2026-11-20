import subprocess
import re
import pathlib

tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata = str(pathlib.Path("backend/data/multimodal/source/_audit").resolve())

devanagari_digits = {'०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'}

def parse_devanagari_num(text):
    # Search for pattern like ॥ १ ॥ or || 1 || or । २३ । or trailing number
    # First find all numbers in danda or double danda
    m = re.findall(r'[॥।|]\s*([०-९\d]+)\s*[॥।|]', text)
    if m:
        num_str = "".join(devanagari_digits.get(c, c) for c in m[-1])
        try:
            return int(num_str)
        except ValueError:
            pass
    # Otherwise find last sequence of devanagari or latin digits
    m = re.findall(r'([०-९\d]+)', text)
    if m:
        num_str = "".join(devanagari_digits.get(c, c) for c in m[-1])
        try:
            return int(num_str)
        except ValueError:
            pass
    return None

test_files = [
    "backend/data/multimodal/source/_audit/frames/ch01/slide001.png",
    "backend/data/multimodal/source/_audit/frames/ch01/slide026.png",
    "backend/data/multimodal/source/_audit/frames/ch01/slide037.png",
    "backend/data/multimodal/source/_audit/frames/ch01/slide046.png",
    "backend/data/multimodal/source/_audit/frames/ch13/slide001.png",
    "backend/data/multimodal/source/_audit/frames/ch13/slide002.png",
    "backend/data/multimodal/source/_audit/frames/ch18/slide078.png"
]

for p in test_files:
    cmd = [tesseract, p, "stdout", "--tessdata-dir", tessdata, "-l", "san+hin", "--psm", "6"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = res.stdout.strip()
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    num = parse_devanagari_num(out)
    print(f"File: {p}")
    print(f"  Detected Num: {num}")
    for idx, l in enumerate(lines):
        print(f"  Line {idx}: {l}")
    print("-" * 50)

