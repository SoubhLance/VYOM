import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

p = 'backend/data/multimodal/source/_audit/frames/ch01/slide022.png'
im = Image.open(p).convert('L')
arr = np.array(im)
logo_mask = np.zeros_like(arr, dtype=bool)
logo_mask[:65, 540:] = True
text_mask = (arr < 160) & (~logo_mask)
row_proj = text_mask.sum(axis=1)

print("Slide 22 row projection for y=50..200:")
for y in range(50, 200, 2):
    bar = '#' * (row_proj[y] // 10)
    print(f"y={y:3d} ({row_proj[y]:3d}): {bar}")

