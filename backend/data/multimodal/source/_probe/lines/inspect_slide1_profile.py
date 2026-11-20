import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

im = Image.open('backend/data/multimodal/source/_audit/frames/ch01/slide001.png').convert('L')
arr = np.array(im)
logo = np.zeros_like(arr, dtype=bool)
logo[:65, 540:] = True
mask = (arr < 160) & (~logo)
mask[215:, :] = False
proj = mask.sum(axis=1)

print("Ch 1 Slide 1 row projection:")
for y in range(40, 180):
    if proj[y] > 0:
        print(f"y={y:3d} ({proj[y]:3d}): {'#' * (proj[y] // 10)}")
    else:
        print(f"y={y:3d} (  0)")

