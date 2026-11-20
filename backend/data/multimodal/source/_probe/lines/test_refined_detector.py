import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

test_slides = [
    (1, 1, 3, "speaker + 2 lines"),
    (1, 20, 3, "3 verse lines"),
    (1, 21, 3, "speaker + 2 lines"),
    (1, 22, 1, "1 verse line"),
    (1, 23, 2, "2 verse lines"),
    (1, 26, 3, "ch1 shifted start: 3 lines"),
    (1, 27, 2, "ch1 shifted: 2 lines"),
    (1, 36, 3, "ch1 shifted end: 3 lines"),
    (4, 24, 2, "2 verse lines"),
    (4, 25, 2, "2 verse lines"),
    (4, 29, 3, "3 lines"),
    (4, 30, 2, "2 lines"),
    (4, 31, 1, "1 line"),
    (6, 22, 2, "2 lines"),
    (6, 23, 1, "1 line"),
    (6, 24, 3, "3 lines"),
    (6, 25, 2, "2 lines"),
    (11, 27, 2, "ch11 long lines: 2 lines"),
    (18, 78, 2, "ch18 final: 2 lines")
]

for ch, sl, exp, desc in test_slides:
    p = f'backend/data/multimodal/source/_audit/frames/ch{ch:02d}/slide{sl:03d}.png'
    arr = np.array(Image.open(p).convert('L'))
    logo = np.zeros_like(arr, dtype=bool)
    logo[:70, 530:] = True
    mask = (arr < 150) & (~logo)
    mask[215:, :] = False
    mask[:15, :] = False
    proj = mask.sum(axis=1)
    
    # Threshold at 35: main body of shirorekha / letters
    active = (proj >= 35)
    
    # Fill small gaps <= 3 rows (e.g. slight dip within the letter body)
    filled = np.copy(active)
    gap_start = None
    for y in range(len(filled)):
        if not filled[y]:
            if gap_start is None: gap_start = y
        else:
            if gap_start is not None:
                if y - gap_start <= 3:
                    filled[gap_start:y] = True
                gap_start = None
                
    # Detect regions
    regions = []
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
                if h >= 8 and peak >= 80:
                    regions.append((reg_start, y - 1, h, peak))
    if in_reg:
        h = len(filled) - reg_start
        peak = proj[reg_start:].max()
        if h >= 8 and peak >= 80:
            regions.append((reg_start, len(filled) - 1, h, peak))
            
    match = (len(regions) == exp)
    status = "OK" if match else "MISMATCH"
    print(f"[{status}] Ch {ch:2d} Sl {sl:3d} (exp={exp}, det={len(regions)}) - {desc}")
    if not match:
        for r in regions:
            print(f"       reg: y={r[0]}..{r[1]} h={r[2]} peak={r[3]}")

