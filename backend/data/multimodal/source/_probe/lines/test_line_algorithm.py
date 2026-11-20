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
    (4, 24, 2, "2 verse lines"),
    (4, 25, 2, "2 verse lines"),
    (4, 29, 3, "3 lines"),
    (4, 30, 2, "2 lines"),
    (4, 31, 1, "1 line"),
    (6, 22, 2, "2 lines"),
    (6, 23, 1, "1 line"),
    (6, 24, 3, "3 lines"),
    (6, 25, 2, "2 lines"),
]

for ch, sl, exp, desc in test_slides:
    p = f'backend/data/multimodal/source/_audit/frames/ch{ch:02d}/slide{sl:03d}.png'
    arr = np.array(Image.open(p).convert('L'))
    
    # 1. Mask top-right logo
    logo = np.zeros_like(arr, dtype=bool)
    logo[:65, 540:] = True
    
    # Also check if there is any bottom edge artifact (e.g. last 5 rows)
    mask = (arr < 160) & (~logo)
    # Zero out very bottom 5 rows if any border noise
    mask[215:, :] = False
    
    proj = mask.sum(axis=1)
    
    # Method 1: Morphological closing / dilation of row projection or gap-merging
    # Text line has width/activity > 20. Gaps within a line (e.g. between matra and shirorekha) are <= 5 rows.
    # Gaps between distinct lines are >= 12 rows.
    
    # Let's see: threshold at proj > 15
    active = (proj >= 15)
    
    # Fill small gaps of <= 8 rows
    filled = np.copy(active)
    gap_start = None
    for y in range(len(filled)):
        if not filled[y]:
            if gap_start is None:
                gap_start = y
        else:
            if gap_start is not None:
                gap_len = y - gap_start
                if gap_len <= 8:
                    filled[gap_start:y] = True
                gap_start = None
                
    # Now find contiguous True regions in filled
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
                # Filter out tiny noise regions (height < 8 or max peak < 50)
                reg_h = y - reg_start
                reg_peak = proj[reg_start:y].max()
                if reg_h >= 10 and reg_peak >= 60:
                    regions.append((reg_start, y - 1, reg_h, reg_peak))
    if in_reg:
        reg_h = len(filled) - reg_start
        reg_peak = proj[reg_start:].max()
        if reg_h >= 10 and reg_peak >= 60:
            regions.append((reg_start, len(filled) - 1, reg_h, reg_peak))
            
    print(f"Ch {ch:2d} Slide {sl:3d} (expected {exp}, {desc}): detected {len(regions)} lines")
    for r in regions:
        print(f"   y={r[0]:3d}..{r[1]:3d} (h={r[2]:2d}, peak={r[3]:3d})")

