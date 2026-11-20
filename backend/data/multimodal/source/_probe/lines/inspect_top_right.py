import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

im = Image.open('backend/data/multimodal/source/_audit/frames/ch01/slide001.png').convert('L')
arr = np.array(im)
text_mask = (arr < 160)

# Check cols for rows 15 to 40
mask_top = text_mask[15:45, :]
col_top = np.where(mask_top.any(axis=0))[0]
if len(col_top) > 0:
    print(f"Rows 15-45 col range: min={col_top[0]}, max={col_top[-1]}")

# Check cols for rows 50 to 220
mask_body = text_mask[50:, :]
col_body = np.where(mask_body.any(axis=0))[0]
if len(col_body) > 0:
    print(f"Rows 50+ col range: min={col_body[0]}, max={col_body[-1]}")

# Check what is in top-right
print("Width:", arr.shape[1], "Height:", arr.shape[0])

