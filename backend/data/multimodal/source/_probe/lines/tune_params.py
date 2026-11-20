import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

for thresh in [15, 18, 20, 22, 25]:
    for min_peak in [50, 60, 70, 80]:
        # Test on Ch 1 Slide 1, Ch 1 Slide 21, Ch 6 Slide 25
        results = []
        for ch, sl in [(1, 1), (1, 21), (6, 25), (1, 20), (1, 22)]:
            p = f'backend/data/multimodal/source/_audit/frames/ch{ch:02d}/slide{sl:03d}.png'
            arr = np.array(Image.open(p).convert('L'))
            logo = np.zeros_like(arr, dtype=bool)
            logo[:70, 530:] = True
            mask = (arr < 150) & (~logo)
            mask[215:, :] = False
            mask[:15, :] = False
            proj = mask.sum(axis=1)
            
            # Smooth with 3-tap filter [1, 2, 1] / 4
            smoothed = np.convolve(proj, [0.25, 0.5, 0.25], mode='same')
            
            active = (smoothed >= thresh)
            
            # Fill gaps <= 4 rows
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
                        
            # Detect regions
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
                        if h >= 8 and peak >= min_peak:
                            regs.append((reg_start, y - 1, h, peak))
            if in_reg:
                h = len(filled) - reg_start
                peak = proj[reg_start:].max()
                if h >= 8 and peak >= min_peak:
                    regs.append((reg_start, len(filled) - 1, h, peak))
            results.append(len(regs))
            
        print(f"thresh={thresh:2d}, min_peak={min_peak:2d} -> Ch1.1={results[0]} (exp 3), Ch1.21={results[1]} (exp 3), Ch6.25={results[2]} (exp 2), Ch1.20={results[3]} (exp 3), Ch1.22={results[4]} (exp 1)")

