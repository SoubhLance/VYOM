import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

im_audit = Image.open('backend/data/multimodal/source/_audit/frames/ch04/slide025.png').convert('L')
im_full = Image.open('backend/data/multimodal/source/_probe/lines/ch04_slide025_start.png').convert('L')

print("Audit frame size:", im_audit.size)
print("Full frame size:", im_full.size)

# Crop the full frame with exact ffmpeg crop: iw*0.68:ih*0.42:iw*0.25:ih*0.08
w, h = im_full.size
crop_x = int(w * 0.25)
crop_y = int(h * 0.08)
crop_w = int(w * 0.68)
crop_h = int(h * 0.42)
cropped = im_full.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
print(f"Crop box: x={crop_x}, y={crop_y}, w={crop_w}, h={crop_h}")

# Let's check where text is vertically in full frame
arr_full = np.array(im_full)
text_mask_full = (arr_full < 160)
row_proj_full = text_mask_full.sum(axis=1)

print("\nFull frame rows with dark pixels (y from 30 to 250):")
for y in range(30, 250, 5):
    cnt = row_proj_full[y]
    if cnt > 50:
        print(f"y={y:3d} ({cnt:4d}): {'#' * (cnt // 30)}")

