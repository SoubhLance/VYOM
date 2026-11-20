import numpy as np
from PIL import Image
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

frames_dir = pathlib.Path('backend/data/multimodal/source/_audit/frames')

# Test threshold sensitivity
thresholds = [120, 140, 150, 160, 170]
test_imgs = [
    'ch01/slide001.png', 'ch01/slide020.png', 'ch01/slide021.png',
    'ch01/slide022.png', 'ch04/slide024.png', 'ch04/slide025.png',
    'ch06/slide022.png', 'ch06/slide023.png', 'ch06/slide024.png',
    'ch06/slide025.png', 'ch11/slide027.png', 'ch18/slide078.png'
]

for name in test_imgs:
    p = frames_dir / name
    arr = np.array(Image.open(p).convert('L'))
    print(f"\n=== {name} ===")
    print(f"min={arr.min()}, p5={np.percentile(arr, 5):.1f}, p50={np.percentile(arr, 50):.1f}, p95={np.percentile(arr, 95):.1f}")

