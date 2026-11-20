import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

p = 'backend/data/multimodal/source/_audit/frames/ch04/slide025.png'
arr = np.array(Image.open(p).convert('L'))
logo_mask = np.zeros_like(arr, dtype=bool)
logo_mask[:65, 540:] = True
text_mask = (arr < 160) & (~logo_mask)
row_proj = text_mask.sum(axis=1)

print("Ch 4 Slide 25 row projection:")
for y in range(30, 180, 2):
    if row_proj[y] > 5:
        bar = '#' * (row_proj[y] // 10)
        print(f"y={y:3d} ({row_proj[y]:3d}): {bar}")
    else:
        if y % 10 == 0:
            print(f"y={y:3d} (  0)")

