import csv
import pathlib
import subprocess
import numpy as np

S = pathlib.Path('backend/data/multimodal/source')
video = str(S / 'lecture.mp4')
ffmpeg = r'C:\Users\Soubh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe'

# Load planned cuts for ch4 and ch12
cuts_ch4 = []
cuts_ch12 = []
with open(S / 'cuts_slides.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        ch = int(r['chapter'])
        if ch == 4:
            cuts_ch4.append(r)
        elif ch == 12:
            cuts_ch12.append(r)

# Test extracting audio for a boundary and inspect RMS
def extract_audio(t_start, t_end):
    cmd = [
        ffmpeg, '-hide_banner', '-loglevel', 'error',
        '-ss', f"{t_start:.4f}", '-to', f"{t_end:.4f}",
        '-i', video,
        '-vn', '-ac', '1', '-ar', '16000',
        '-f', 'f32le', 'pipe:'
    ]
    res = subprocess.run(cmd, capture_output=True)
    return np.frombuffer(res.stdout, dtype=np.float32)

# Test on first internal boundary of Ch 4
t = float(cuts_ch4[1]['start'])
audio = extract_audio(t - 1.0, t + 3.0)
print(f"Ch 4 first internal boundary t={t:.3f}, samples={len(audio)}")

# Compute RMS in 50 ms steps with 100 ms window
# 100 ms = 1600 samples, 50 ms = 800 samples
win_len = 1600
step = 800
n_steps = (len(audio) - win_len) // step + 1

rms_vals = []
offsets = []
for i in range(n_steps):
    s = i * step
    chunk = audio[s : s + win_len]
    rms = np.sqrt(np.mean(chunk**2))
    t_offset_start = (s - 16000) / 16000.0  # relative to t
    t_offset_center = t_offset_start + 0.050
    rms_vals.append((t_offset_start, t_offset_center, rms))

# Median RMS across the full 4.0s window [t-1.0, t+3.0]
all_rms = [r[2] for r in rms_vals]
med_rms = np.median(all_rms)

# Find lowest RMS between t and t+2.5
# Candidate windows where start is between 0.0 and 2.5 (or window fully within [0.0, 2.5])
cands = [r for r in rms_vals if 0.0 <= r[0] <= 2.4] # window ends by 2.5
min_cand = min(cands, key=lambda x: x[2])
min_offset_start, min_offset_center, min_rms = min_cand

depth_db = 20 * np.log10(med_rms / max(min_rms, 1e-9))
print(f"Median RMS: {med_rms:.6f} ({20*np.log10(med_rms):.2f} dBFS)")
print(f"Lowest RMS in [t, t+2.5]: {min_rms:.6f} ({20*np.log10(min_rms):.2f} dBFS)")
print(f"Dip offset (start): {min_offset_start:.3f} s, Dip offset (center): {min_offset_center:.3f} s")
print(f"Dip depth below median RMS: {depth_db:.2f} dB")

