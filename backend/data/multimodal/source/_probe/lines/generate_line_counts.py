import csv
import json
import numpy as np
import pathlib
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
frames_dir = S / '_audit' / 'frames'
v3_path = S / 'vyom_clips_v3.json'
out_csv = S / '_probe' / 'lines' / 'line_counts.csv'

with open(v3_path, encoding='utf-8') as f:
    clips_v3 = json.load(f)
clips_by_cs = {(c['chapter'], c['slide']): c for c in clips_v3}

rows = []
mismatches = []

for ch in range(1, 19):
    ch_dir = frames_dir / f'ch{ch:02d}'
    for sl_file in sorted(ch_dir.glob('slide*.png')):
        sl = int(sl_file.stem.replace('slide', ''))
        clip = clips_by_cs[(ch, sl)]
        
        arr = np.array(Image.open(sl_file).convert('L'))
        
        # 1. Mask top-right logo: x >= 530, y <= 70
        logo = np.zeros_like(arr, dtype=bool)
        logo[:70, 530:] = True
        
        # 2. Text pixel threshold: < 150
        mask = (arr < 150) & (~logo)
        
        # 3. Suppress borders: top 15 rows, bottom 7 rows
        mask[:15, :] = False
        mask[215:, :] = False
        
        # 4. Horizontal projection
        proj = mask.sum(axis=1)
        
        # 5. Smoothing with 3-tap filter
        smoothed = np.convolve(proj, [0.25, 0.5, 0.25], mode='same')
        
        # 6. Activity threshold
        active = (smoothed >= 20)
        
        # 7. Bridge intra-line gaps <= 4 rows
        filled = np.copy(active)
        gap_start = None
        for y in range(len(filled)):
            if not filled[y]:
                if gap_start is None: gap_start = y
            else:
                if gap_start is not None:
                    if y - gap_start <= 4:
                        filled[gap_start:y] = True
                    gap_start = None
                    
        # 8. Contiguous regions with height >= 8 and peak >= 60
        regs = []
        in_reg = False
        reg_start = None
        for y in range(len(filled)):
            if filled[y]:
                if not in_reg:
                    in_reg = True
                    reg_start = y
            else:
                if in_reg:
                    in_reg = False
                    h = y - reg_start
                    peak = proj[reg_start:y].max()
                    if h >= 8 and peak >= 60:
                        regs.append((reg_start, y - 1, h, peak))
        if in_reg:
            h = len(filled) - reg_start
            peak = proj[reg_start:].max()
            if h >= 8 and peak >= 60:
                regs.append((reg_start, len(filled) - 1, h, peak))
                
        det = len(regs)
        n_spoken = len(clip['spoken_lines'])
        has_speaker = (clip['speaker'] is not None)
        exp = n_spoken + (1 if has_speaker else 0)
        mismatch = (det != exp)
        
        row_dict = {
            'chapter': ch,
            'slide': sl,
            'detected_lines': det,
            'expected_lines': exp,
            'mismatch': mismatch
        }
        rows.append(row_dict)
        if mismatch:
            mismatches.append((ch, sl, det, exp, clip['speaker'], clip['spoken_lines'], regs))

# Write CSV
with open(out_csv, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['chapter', 'slide', 'detected_lines', 'expected_lines', 'mismatch'])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {out_csv} with {len(rows)} rows.")
print(f"Total mismatches: {len(mismatches)}")
print("\n=== MISMATCH ROWS ===")
for ch, sl, det, exp, sp, splines, regs in mismatches:
    print(f"Chapter {ch:2d}, Slide {sl:3d}: detected={det}, expected={exp} | speaker={sp}")

