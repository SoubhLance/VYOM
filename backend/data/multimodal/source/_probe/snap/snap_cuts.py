import csv
import pathlib
import subprocess
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
video = str(S / 'lecture.mp4')
ffmpeg = r'C:\Users\Soubh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe'
snap_dir = S / '_probe' / 'snap'
snap_dir.mkdir(parents=True, exist_ok=True)
out_csv = snap_dir / 'cuts_snapped.csv'

# 1. Load inputs: S/cuts_ch01_46.csv for chapter 1, and S/cuts_slides.csv for chapters 2-18
input_rows = []
with open(S / 'cuts_ch01_46.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        input_rows.append(r)
with open(S / 'cuts_slides.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if int(r['chapter']) >= 2:
            input_rows.append(r)

print(f"Loaded {len(input_rows)} input clip rows across 18 chapters.")

# Group rows by chapter
ch_rows = {}
for r in input_rows:
    ch = int(r['chapter'])
    ch_rows.setdefault(ch, []).append(r)

fs = 16000
win_len = int(0.100 * fs) # 100 ms = 1600 samples
step = int(0.050 * fs)    # 50 ms = 800 samples

all_snapped_rows = []
chapter_stats = {}
all_fallback_rows = []

for ch in range(1, 19):
    rows = ch_rows[ch]
    n_clips = len(rows)
    n_boundaries = n_clips - 1
    
    first_start = float(rows[0]['start'])
    last_end = float(rows[-1]['end'])
    
    # Internal boundaries t: start of each slide except the first
    # t_1, t_2, ..., t_{n-1}
    orig_t_list = [float(rows[i]['start']) for i in range(1, n_clips)]
    
    # Extract audio for the chapter with 2s margin
    t_min = min(first_start, orig_t_list[0]) - 2.0
    t_max = max(last_end, orig_t_list[-1]) + 4.0
    
    cmd = [
        ffmpeg, '-hide_banner', '-loglevel', 'error',
        '-ss', f"{t_min:.4f}", '-to', f"{t_max:.4f}",
        '-i', video,
        '-vn', '-ac', '1', '-ar', str(fs),
        '-f', 'f32le', 'pipe:'
    ]
    res = subprocess.run(cmd, capture_output=True)
    ch_audio = np.frombuffer(res.stdout, dtype=np.float32)
    
    snapped_t_list = []
    final_offsets = []
    applied_offsets_for_stats = []
    depths_list = []
    fallbacks = []
    
    for i, t in enumerate(orig_t_list):
        slide_idx = i + 2 # 1-based slide number starting at this boundary
        st_sec = t - 1.0
        en_sec = t + 3.0
        st_sample = int(round((st_sec - t_min) * fs))
        en_sample = int(round((en_sec - t_min) * fs))
        
        chunk_4s = ch_audio[st_sample : en_sample]
        if len(chunk_4s) < 4 * fs:
            # Fallback if audio boundary slice is short
            cmd_s = [
                ffmpeg, '-hide_banner', '-loglevel', 'error',
                '-ss', f"{st_sec:.4f}", '-to', f"{en_sec:.4f}",
                '-i', video,
                '-vn', '-ac', '1', '-ar', str(fs),
                '-f', 'f32le', 'pipe:'
            ]
            res_s = subprocess.run(cmd_s, capture_output=True)
            chunk_4s = np.frombuffer(res_s.stdout, dtype=np.float32)
            
        n_steps = (len(chunk_4s) - win_len) // step + 1
        rms_vals = []
        for s_i in range(n_steps):
            s = s_i * step
            w = chunk_4s[s : s + win_len]
            r = np.sqrt(np.mean(w**2))
            off = (s - int(1.0 * fs)) / fs
            rms_vals.append((off, r))
            
        all_rms = [x[1] for x in rms_vals]
        med_rms = float(np.median(all_rms))
        
        # Candidate windows between t - 0.5 and t + 2.5
        cands = [x for x in rms_vals if -0.5001 <= x[0] <= 2.4501]
        min_cand = min(cands, key=lambda x: x[1])
        raw_off = min_cand[0]
        min_rms = min_cand[1]
        
        depth_db = 20.0 * np.log10(med_rms / max(min_rms, 1e-9))
        depths_list.append(depth_db)
        
        # Rule: Snapped boundary = t + offset + 0.05.
        # If depth < 10 dB or offset > 2.0, use t + 0.9 instead and add flag SNAP_FALLBACK.
        is_fallback = (depth_db < 10.0) or (raw_off > 2.0)
        fallbacks.append(is_fallback)
        
        if is_fallback:
            final_off = 0.900
            snapped_t = t + 0.900
        else:
            final_off = raw_off + 0.050
            snapped_t = t + final_off
            
        snapped_t_list.append(snapped_t)
        final_offsets.append(final_off)
        applied_offsets_for_stats.append(final_off)
        
    # Build complete boundary points for the chapter:
    # T_0 = first_start (unchanged)
    # T_1..T_{n-1} = snapped_t_list
    # T_n = last_end (unchanged)
    T_points = [first_start] + snapped_t_list + [last_end]
    
    # Construct output rows for this chapter
    for k in range(n_clips):
        orig_r = rows[k]
        c = int(orig_r['chapter'])
        v = int(orig_r.get('verse', orig_r.get('slide', k+1)))
        
        c_st = T_points[k]
        c_en = T_points[k+1]
        dur = c_en - c_st
        
        # Existing flags
        orig_flags = [f.strip() for f in orig_r.get('flags', '').split('|') if f.strip()]
        
        # Flags for fallback:
        # If clip starts at an internal boundary that used fallback
        # k=0 is slide 1 (starts at first_start, unchanged)
        # k>=1 is slide k+1 (starts at boundary k-1)
        if k > 0 and fallbacks[k - 1]:
            if 'SNAP_FALLBACK' not in orig_flags:
                orig_flags.append('SNAP_FALLBACK')
                
        # snap_offset and snap_depth_db for this clip's start
        if k == 0:
            snap_off_str = "0.000"
            snap_dep_str = "0.00"
        else:
            snap_off_str = f"{final_offsets[k - 1]:.3f}"
            snap_dep_str = f"{depths_list[k - 1]:.2f}"
            
        row_dict = {
            'chapter': c,
            'verse': v,
            'start': f"{c_st:.3f}",
            'end': f"{c_en:.3f}",
            'dur_sec': f"{dur:.1f}",
            'flags': "|".join(orig_flags),
            'snap_offset': snap_off_str,
            'snap_depth_db': snap_dep_str
        }
        all_snapped_rows.append(row_dict)
        
        if k > 0 and fallbacks[k - 1]:
            all_fallback_rows.append((c, v, orig_t_list[k - 1], orig_t_list[k - 1] + 0.900, depths_list[k - 1], row_dict))
            
    # Stats per chapter
    fb_count = sum(1 for fb in fallbacks if fb)
    med_off = float(np.median(applied_offsets_for_stats))
    std_off = float(np.std(applied_offsets_for_stats))
    chapter_stats[ch] = {
        'boundaries': n_boundaries,
        'fallback_count': fb_count,
        'med_offset': med_off,
        'std_offset': std_off
    }

# 3. Output S/cuts_snapped.csv
with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['chapter', 'verse', 'start', 'end', 'dur_sec', 'flags', 'snap_offset', 'snap_depth_db']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_snapped_rows)

print(f"\nWrote {out_csv}: {len(all_snapped_rows)} clips.")

# Verify invariants:
# 1. Each clip's end must equal the next clip's start (within each chapter)
# 2. No clip is under 3 s
under_3s = []
mismatched_boundaries = []
negative_dur = []

ch_snapped = {}
for r in all_snapped_rows:
    ch_snapped.setdefault(int(r['chapter']), []).append(r)

for ch in range(1, 19):
    c_rows = ch_snapped[ch]
    for k in range(len(c_rows)):
        st = float(c_rows[k]['start'])
        en = float(c_rows[k]['end'])
        dur = float(c_rows[k]['dur_sec'])
        if dur <= 0:
            negative_dur.append((ch, k+1, st, en, dur))
        if dur < 3.0:
            under_3s.append((ch, k+1, st, en, dur))
        if k < len(c_rows) - 1:
            nxt_st = float(c_rows[k+1]['start'])
            if abs(en - nxt_st) > 0.001:
                mismatched_boundaries.append((ch, k+1, en, nxt_st))

print(f"Verification Invariants:")
print(f"  Boundary match between consecutive clips: {'PERFECT (0 mismatches)' if not mismatched_boundaries else f'{len(mismatched_boundaries)} MISMATCHES'}")
print(f"  Negative durations: {len(negative_dur)}")
print(f"  Clips under 3.0s: {len(under_3s)}")
if under_3s:
    for x in under_3s:
        print(f"    UNDER 3s: Ch {x[0]} slide {x[1]}: start={x[2]:.3f}, end={x[3]:.3f}, dur={x[4]:.3f}s")

# 4. Print per chapter stats and fallback list
print("\n=== PER-CHAPTER SNAP STATISTICS ===")
print("Ch | Boundaries | Fallbacks | Median Final Offset (s) | Std Dev (s)")
for ch in range(1, 19):
    st = chapter_stats[ch]
    print(f"{ch:2d} | {st['boundaries']:10d} | {st['fallback_count']:9d} | {st['med_offset']:23.3f} | {st['std_offset']:11.3f}")

total_fb = len(all_fallback_rows)
print(f"\nTotal Fallback Rows Across All Chapters: {total_fb}")
print("List of Every Fallback Row:")
for c, v, orig_t, sn_t, depth, r in all_fallback_rows:
    print(f"  Ch {c:2d} Slide {v:2d} | orig_t={orig_t:8.3f}s -> snapped_t={sn_t:8.3f}s (+0.900s) | depth={depth:5.1f}dB | flags: {r['flags']}")

