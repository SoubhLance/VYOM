import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Let's inspect slide001 (speaker: धृतराष्ट्र उवाच, 2 verse lines -> total 3 lines)
# slide020 (no speaker, 2 verse lines -> total 2 lines)
# slide021 (speaker: अर्जुन उवाच, 2 verse lines -> total 3 lines)
# slide022 (score was low: 0.617 - let's see how many lines it actually has!)

for sl in ['slide001.png', 'slide020.png', 'slide021.png', 'slide022.png', 'slide023.png']:
    p = f'backend/data/multimodal/source/_audit/frames/ch01/{sl}'
    arr = np.array(Image.open(p).convert('L'))
    
    # Mask out top-right logo: e.g. y < 65 and x >= 540
    logo_mask = np.zeros_like(arr, dtype=bool)
    logo_mask[:65, 540:] = True
    
    text_mask = (arr < 160) & (~logo_mask)
    row_proj = text_mask.sum(axis=1)
    
    print(f"=== {sl} ===")
    # Print row projection where > 5
    active_rows = np.where(row_proj > 10)[0]
    print(f"Active rows range: {active_rows[0]} to {active_rows[-1]}")
    
    # Group contiguous rows where row_proj > threshold (e.g. 15 or 20)
    thresh = 15
    in_line = False
    lines = []
    curr_start = None
    for y, count in enumerate(row_proj):
        if count >= thresh:
            if not in_line:
                in_line = True
                curr_start = y
        else:
            if in_line:
                in_line = False
                lines.append((curr_start, y - 1, int(row_proj[curr_start:y].max())))
    if in_line:
        lines.append((curr_start, len(row_proj) - 1, int(row_proj[curr_start:].max())))
        
    print(f"Detected lines (count={len(lines)}):")
    for start, end, max_val in lines:
        print(f"  y={start:3d}..{end:3d} (height={end-start+1:2d}, peak={max_val:3d})")

