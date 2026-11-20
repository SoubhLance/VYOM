import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

img_paths = [
    'backend/data/multimodal/source/_audit/frames/ch01/slide001.png',
    'backend/data/multimodal/source/_audit/frames/ch01/slide021.png',
    'backend/data/multimodal/source/_audit/frames/ch01/slide022.png',
    'backend/data/multimodal/source/_audit/frames/ch04/slide025.png',
    'backend/data/multimodal/source/_audit/frames/ch06/slide023.png',
]

for p in img_paths:
    im = Image.open(p).convert('L') # Grayscale
    arr = np.array(im)
    print(f"=== {p} ===")
    print(f"Shape: {arr.shape}, dtype: {arr.dtype}")
    print(f"Min: {arr.min()}, Max: {arr.max()}, Mean: {arr.mean():.1f}, Median: {np.median(arr)}")
    # Print sample corner and center
    print(f"Top-left (10x10 mean): {arr[:10, :10].mean():.1f}")
    print(f"Center (10x10 mean): {arr[350:360, 630:640].mean():.1f}")

