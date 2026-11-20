import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

for p in [
    'backend/data/multimodal/source/_audit/frames/ch01/slide001.png',
    'backend/data/multimodal/source/_audit/frames/ch01/slide020.png',
    'backend/data/multimodal/source/_audit/frames/ch01/slide021.png',
    'backend/data/multimodal/source/_audit/frames/ch01/slide022.png',
    'backend/data/multimodal/source/_audit/frames/ch04/slide025.png',
]:
    arr = np.array(Image.open(p).convert('L'))
    # Invert so text is high value: background is ~250, text is dark (<150)
    text_mask = (arr < 160) # dark pixels
    
    # Check where text is horizontally
    col_proj = text_mask.sum(axis=0)
    row_proj = text_mask.sum(axis=1)
    
    print(f"=== {p} ===")
    print("Col proj top 5 maxes:", np.sort(col_proj)[-5:])
    print("Row proj min, median, max:", row_proj.min(), np.median(row_proj), row_proj.max())
    # Find rows where text exists
    text_rows = np.where(row_proj > 10)[0]
    if len(text_rows) > 0:
        print(f"Text row range: {text_rows[0]} to {text_rows[-1]}")
    # Show projection pattern
    print("Sample row projection (every 5 rows):", row_proj[::10])

