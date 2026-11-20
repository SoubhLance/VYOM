import json
import numpy as np
import pathlib
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
frames_dir = S / '_audit' / 'frames'
v3_path = S / 'vyom_clips_v3.json'

with open(v3_path, encoding='utf-8') as f:
    clips_v3 = json.load(f)
clips_by_cs = {(c['chapter'], c['slide']): c for c in clips_v3}

results = []

for ch in range(1, 19):
    ch_dir = frames_dir / f'ch{ch:02d}'
    for sl_file in sorted(ch_dir.glob('slide*.png')):
        # parse slide number
        sl = int(sl_file.stem.replace('slide', ''))
        clip = clips_by_cs[(ch, sl)]
        
        arr = np.array(Image.open(sl_file).convert('L'))
        logo = np.zeros_like(arr, dtype=bool)
        logo[:70, 530:] = True
        mask = (arr < 150) & (~logo)
        mask[215:, :] = False
        mask[:15, :] = False
        proj = mask.sum(axis=1)
        
        # Smooth with [0.25, 0.5, 0.25]
        smoothed = np.convolve(proj, [0.25, 0.5, 0.25], mode='same')
        active = (smoothed >= 20)
        
        # Fill gaps <= 4 rows
        filled = np.copy(active)
        gap_start = None
        for y in range(len(filled)):
            if not filled[y]:
                if gap_start is None: gap_start = y
            else:
                if gap_start is not None:
                    if y - gap_start <= 4:
                        filled[gap_start:y] = True
                    gap_start = None
                    
        # Find contiguous regions
        regs = []
        in_reg = False
        reg_start = None
        for y in range(len(filled)):
            if filled[y]:
                if not in_reg:
                    in_reg = True
                    reg_start = y
            else:
                if in_reg:
                    in_reg = False
                    h = y - reg_start
                    peak = proj[reg_start:y].max()
                    if h >= 8 and peak >= 60:
                        regs.append((reg_start, y - 1, h, peak))
        if in_reg:
            h = len(filled) - reg_start
            peak = proj[reg_start:].max()
            if h >= 8 and peak >= 60:
                regs.append((reg_start, len(filled) - 1, h, peak))
                
        det = len(regs)
        
        # Expected lines:
        # Spoken lines count
        n_spoken = len(clip['spoken_lines'])
        has_speaker = (clip['speaker'] is not None)
        exp_spoken = n_spoken + (1 if has_speaker else 0)
        
        # Alternative expected lines: 2 per verse + speaker
        n_verses = len(clip['data_verses'])
        exp_verses = 2 * n_verses + (1 if has_speaker else 0)
        
        results.append({
            'chapter': ch,
            'slide': sl,
            'detected': det,
            'exp_spoken': exp_spoken,
            'exp_verses': exp_verses,
            'n_spoken': n_spoken,
            'has_speaker': has_speaker,
            'speaker': clip['speaker'],
            'regions': regs
        })

# Print summary
mismatches_spoken = [r for r in results if r['detected'] != r['exp_spoken']]
print(f"Total slides: {len(results)}")
print(f"Mismatches against exp_spoken: {len(mismatches_spoken)}")

for m in mismatches_spoken:
    print(f"Ch {m['chapter']:2d} Slide {m['slide']:3d}: detected={m['detected']}, exp={m['exp_spoken']} (spoken={m['n_spoken']}, speaker={m['speaker']})")
    for r in m['regions']:
        print(f"    reg: y={r[0]}..{r[1]} h={r[2]} peak={r[3]}")

