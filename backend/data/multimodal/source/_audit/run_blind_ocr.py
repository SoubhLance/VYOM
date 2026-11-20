import csv
import subprocess
import re
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
audit_dir = S / '_audit'
frames_dir = audit_dir / 'frames'
out_csv = audit_dir / 'ocr_blind.csv'

tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata = str(audit_dir.resolve())

devanagari_digits = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

# Common Tesseract digit confusions for Devanagari numerals:
# ४ (4) often read as 8 or ४
# १ (1) often read as 9 or १
# ५ (5) often read as 4 or y
# ६ (6) often read as ६ or ६

def parse_onscreen_num(lines):
    # Scan lines from bottom to top for verse numbers in danda
    for l in reversed(lines):
        # Look for ॥ num ॥ or | num |
        m = re.findall(r'[॥।|]\s*([०-९\d]+)\s*[॥।|]', l)
        if m:
            num_str = "".join(devanagari_digits.get(c, c) for c in m[-1])
            try:
                return int(num_str)
            except ValueError:
                pass
        # Look for trailing ॥ num
        m2 = re.findall(r'[॥।|]\s*([०-९\d]+)\s*$', l)
        if m2:
            num_str = "".join(devanagari_digits.get(c, c) for c in m2[-1])
            try:
                return int(num_str)
            except ValueError:
                pass
    # If no danda pattern, look for any digit at end of last line
    if lines:
        last = lines[-1]
        m3 = re.findall(r'([०-९\d]+)\s*[॥।|]?\s*$', last)
        if m3:
            num_str = "".join(devanagari_digits.get(c, c) for c in m3[-1])
            try:
                return int(num_str)
            except ValueError:
                pass
    return ""

def clean_ocr_text(raw_text):
    raw_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    cleaned = []
    for l in raw_lines:
        # Filter top watermark noise
        if any(w in l.upper() for w in ['HARE', 'TELEVI', 'K', '|K']) and len(l) < 15:
            continue
        if re.match(r'^[1१॥|!+०-९\s<\|/]+$', l) and len(l) < 10:
            continue
        # Filter bottom artifact (single character)
        if len(l) <= 2 and not any(d in l for d in '०१२३४५६७८९0123456789'):
            continue
        cleaned.append(l)
    return cleaned

speaker_patterns = [
    'धृतराष्ट्र उवाच', 'घृतराष्र उवाच', 'सञ्जय उवाच', 'सब्नय उवाच', 'सञ्चय उवाच',
    'अर्जुन उवाच', 'श्रीभगवानुवाच', 'श्री भगवानुवाच', 'भगवानुवाच'
]

def extract_speaker(lines):
    if not lines:
        return "", lines
    first = lines[0]
    # Check if first line is purely speaker label
    for sp in speaker_patterns:
        if sp in first:
            # Check if verse text is glued after speaker
            idx = first.find('उवाच')
            if idx != -1:
                sp_label = first[:idx+4].strip()
                rest = first[idx+4:].strip()
                # remove optional colon, danda
                rest = re.sub(r'^[:|।॥\s]+', '', rest)
                rem_lines = lines[1:]
                if rest:
                    rem_lines = [rest] + rem_lines
                return sp_label, rem_lines
    return "", lines

# Discover all frames
frame_files = sorted(list(frames_dir.glob("ch*/slide*.png")))
print(f"Found {len(frame_files)} frames to transcribe blind with Tesseract OCR (san+hin)...")

out_rows = []
errors = 0

for i, p in enumerate(frame_files):
    # Determine chapter and slide from path
    ch = int(p.parent.name.replace('ch', ''))
    sl = int(p.stem.replace('slide', ''))
    
    cmd = [tesseract, str(p), "stdout", "--tessdata-dir", tessdata, "-l", "san+hin", "--psm", "6"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    raw = res.stdout.strip()
    
    if not raw:
        out_rows.append({
            'chapter': ch, 'slide': sl, 'onscreen_number': 'UNREADABLE',
            'speaker_label': '', 'line1': 'UNREADABLE', 'line2': '', 'line3': ''
        })
        errors += 1
        continue
        
    cleaned_lines = clean_ocr_text(raw)
    if not cleaned_lines:
        out_rows.append({
            'chapter': ch, 'slide': sl, 'onscreen_number': 'UNREADABLE',
            'speaker_label': '', 'line1': 'UNREADABLE', 'line2': '', 'line3': ''
        })
        errors += 1
        continue
        
    onscreen_num = parse_onscreen_num(cleaned_lines)
    sp_label, v_lines = extract_speaker(cleaned_lines)
    
    line1 = v_lines[0] if len(v_lines) > 0 else ""
    line2 = v_lines[1] if len(v_lines) > 1 else ""
    line3 = " ".join(v_lines[2:]) if len(v_lines) > 2 else ""
    
    out_rows.append({
        'chapter': ch,
        'slide': sl,
        'onscreen_number': onscreen_num,
        'speaker_label': sp_label,
        'line1': line1,
        'line2': line2,
        'line3': line3
    })
    
    if (i + 1) % 100 == 0:
        print(f"  Processed {i + 1}/{len(frame_files)} frames...")

# Write to _audit/ocr_blind.csv
with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['chapter', 'slide', 'onscreen_number', 'speaker_label', 'line1', 'line2', 'line3'])
    writer.writeheader()
    writer.writerows(out_rows)

print(f"\nDone: Transcribed {len(out_rows)} frames to {out_csv} ({errors} unreadable)")

