import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

for p in [
    'backend/data/multimodal/source/_audit/frames/ch01/slide001.png',
    'backend/data/multimodal/source/_audit/frames/ch02/slide010.png',
    'backend/data/multimodal/source/_audit/frames/ch05/slide005.png',
    'backend/data/multimodal/source/_audit/frames/ch10/slide020.png',
    'backend/data/multimodal/source/_audit/frames/ch18/slide050.png',
]:
    arr = np.array(Image.open(p).convert('L'))
    text_mask = (arr < 160)
    top_mask = text_mask[:60, :]
    ys, xs = np.where(top_mask)
    if len(xs) > 0:
        print(f"{p}: top rows xs min={xs.min()}, max={xs.max()}, ys min={ys.min()}, max={ys.max()}")
    else:
        print(f"{p}: no dark pixels in top 60 rows")

