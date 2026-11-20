import csv
import pathlib
import subprocess
import numpy as np

S = pathlib.Path('backend/data/multimodal/source')
video = str(S / 'lecture.mp4')
ffmpeg = r'C:\Users\Soubh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe'
shift_dir = S / '_probe' / 'shift'
shift_dir.mkdir(parents=True, exist_ok=True)

# Load planned cuts
cuts_ch4 = []
cuts_ch12 = []
with open(S / 'cuts_slides.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        ch = int(r['chapter'])
        if ch == 4:
            cuts_ch4.append(r)
        elif ch == 12:
            cuts_ch12.append(r)

# Internal boundaries: start of every slide except the first
# Ch 4: slides 2 to 42 (41 boundaries)
# Ch 12: slides 2 to 20 (19 boundaries)

def process_chapter(ch_num, cuts):
    boundaries = []
    # slides 2 to N
    for i in range(1, len(cuts)):
        r = cuts[i]
        b_idx = i # 1-based internal boundary index (1 to N-1)
        slide_num = int(r.get('verse', r.get('slide', i+1)))
        t = float(r['start'])
        boundaries.append((b_idx, slide_num, t))
    
    # Extract audio for each boundary
    results = []
    
    # Extract entire chapter range with margin to make extraction fast and robust
    t_min = min(b[2] for b in boundaries) - 2.0
    t_max = max(b[2] for b in boundaries) + 4.0
    cmd = [
        ffmpeg, '-hide_banner', '-loglevel', 'error',
        '-ss', f"{t_min:.4f}", '-to', f"{t_max:.4f}",
        '-i', video,
        '-vn', '-ac', '1', '-ar', '16000',
        '-f', 'f32le', 'pipe:'
    ]
    res = subprocess.run(cmd, capture_output=True)
    ch_audio = np.frombuffer(res.stdout, dtype=np.float32)
    
    # Sample rate = 16000
    fs = 16000
    win_len = int(0.100 * fs) # 100 ms = 1600 samples
    step = int(0.050 * fs)    # 50 ms = 800 samples
    
    for b_idx, slide_num, t in boundaries:
        # Extract [t - 1.0, t + 3.0]
        st_sec = t - 1.0
        en_sec = t + 3.0
        st_idx = int(round((st_sec - t_min) * fs))
        en_idx = int(round((en_sec - t_min) * fs))
        
        audio = ch_audio[st_idx : en_idx]
        if len(audio) < 4 * fs:
            # Fallback direct ffmpeg extract if boundary margin edge
            cmd_single = [
                ffmpeg, '-hide_banner', '-loglevel', 'error',
                '-ss', f"{st_sec:.4f}", '-to', f"{en_sec:.4f}",
                '-i', video,
                '-vn', '-ac', '1', '-ar', '16000',
                '-f', 'f32le', 'pipe:'
            ]
            res_single = subprocess.run(cmd_single, capture_output=True)
            audio = np.frombuffer(res_single.stdout, dtype=np.float32)
            
        # Compute RMS in 50 ms steps for [t - 1.0, t + 3.0]
        # In this 4.0 s window:
        # t is at 1.0 s -> sample 16000
        # t + 2.5 is at 3.5 s -> sample 56000
        
        n_steps = (len(audio) - win_len) // step + 1
        rms_vals = []
        for s_i in range(n_steps):
            sample_start = s_i * step
            chunk = audio[sample_start : sample_start + win_len]
            rms = np.sqrt(np.mean(chunk**2))
            
            # offset of window start from t (in seconds)
            offset_start = (sample_start - int(1.0 * fs)) / fs
            # offset of window center from t (in seconds)
            offset_center = offset_start + 0.050
            rms_vals.append((offset_start, offset_center, rms))
            
        # Median RMS across the 4.0s window [t-1.0, t+3.0]
        all_rms = [x[2] for x in rms_vals]
        med_rms = float(np.median(all_rms))
        
        # Search for lowest-RMS 100 ms window between t and t+2.5
        # Start of window >= 0.0 and end of window <= 2.5 (i.e. start <= 2.4)
        cands = [x for x in rms_vals if 0.0 <= round(x[0], 4) <= 2.4]
        min_cand = min(cands, key=lambda x: x[2])
        
        dip_offset = min_cand[0] # window start offset from t
        dip_rms = min_cand[2]
        
        # Depth in dB below the median RMS of the window
        dip_depth_db = 20.0 * np.log10(med_rms / max(dip_rms, 1e-9))
        
        results.append({
            'boundary': b_idx,
            'slide': slide_num,
            't': t,
            'dip_offset': dip_offset,
            'dip_offset_center': min_cand[1],
            'dip_depth_db': dip_depth_db,
            'med_rms_db': 20.0 * np.log10(max(med_rms, 1e-9)),
            'dip_rms_db': 20.0 * np.log10(max(dip_rms, 1e-9))
        })
        
    return results

res_ch4 = process_chapter(4, cuts_ch4)
res_ch12 = process_chapter(12, cuts_ch12)

# Save shift_ch04.csv and shift_ch12.csv
# Columns: boundary, t, dip_offset, dip_depth_db
for ch_num, res, fname in [(4, res_ch4, 'shift_ch04.csv'), (12, res_ch12, 'shift_ch12.csv')]:
    csv_path = shift_dir / fname
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['boundary', 't', 'dip_offset', 'dip_depth_db'])
        for r in res:
            writer.writerow([r['boundary'], f"{r['t']:.3f}", f"{r['dip_offset']:.3f}", f"{r['dip_depth_db']:.2f}"])
    print(f"Wrote {csv_path}: {len(res)} rows")

# Print statistics for each chapter
for ch_name, res in [('Chapter 4', res_ch4), ('Chapter 12', res_ch12)]:
    offsets = [r['dip_offset'] for r in res]
    depths = [r['dip_depth_db'] for r in res]
    shallow_count = sum(1 for d in depths if d < 3.0)
    
    med_off = np.median(offsets)
    min_off = np.min(offsets)
    max_off = np.max(offsets)
    std_off = np.std(offsets)
    
    med_depth = np.median(depths)
    
    print(f"\n=== {ch_name} Statistics ({len(res)} internal boundaries) ===")
    print(f"  dip_offset: median = {med_off:.3f} s, min = {min_off:.3f} s, max = {max_off:.3f} s, std = {std_off:.3f} s")
    print(f"  dip_depth:  median = {med_depth:.2f} dB, min = {min(depths):.2f} dB, max = {max(depths):.2f} dB")
    print(f"  Boundaries with dip shallower than 3 dB: {shallow_count} / {len(res)}")

