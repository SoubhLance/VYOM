import numpy as np
from PIL import Image
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

frames_dir = pathlib.Path('backend/data/multimodal/source/_audit/frames')

min_active_y = []
max_active_y = []
max_proj_vals = []

for ch in range(1, 19):
    for p in sorted((frames_dir / f'ch{ch:02d}').glob('slide*.png')):
        arr = np.array(Image.open(p).convert('L'))
        # mask logo: y < 65, x >= 540
        logo = np.zeros_like(arr, dtype=bool)
        logo[:65, 540:] = True
        mask = (arr < 160) & (~logo)
        proj = mask.sum(axis=1)
        active = np.where(proj > 20)[0]
        if len(active) > 0:
            min_active_y.append(active[0])
            max_active_y.append(active[-1])
            max_proj_vals.append(proj.max())

print(f"Total frames checked: {len(min_active_y)}")
print(f"Min active y: {min(min_active_y)}, Max active y: {max(max_active_y)}")
print(f"Min peak proj: {min(max_proj_vals)}, Max peak proj: {max(max_proj_vals)}")

