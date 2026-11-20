import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

for name, p in [
    ('Slide 20', 'backend/data/multimodal/source/_audit/frames/ch01/slide020.png'),
    ('Slide 21', 'backend/data/multimodal/source/_audit/frames/ch01/slide021.png'),
    ('Slide 22', 'backend/data/multimodal/source/_audit/frames/ch01/slide022.png'),
    ('Slide 23', 'backend/data/multimodal/source/_audit/frames/ch01/slide023.png'),
]:
    arr = np.array(Image.open(p).convert('L'))
    logo_mask = np.zeros_like(arr, dtype=bool)
    logo_mask[:65, 540:] = True
    text_mask = (arr < 160) & (~logo_mask)
    row_proj = text_mask.sum(axis=1)

    print(f"\n=== {name} ===")
    for y in range(40, 185, 2):
        if row_proj[y] > 10:
            bar = '#' * (row_proj[y] // 15)
            print(f"y={y:3d} ({row_proj[y]:3d}): {bar}")
        else:
            if y % 10 == 0:
                print(f"y={y:3d} (  0)")

