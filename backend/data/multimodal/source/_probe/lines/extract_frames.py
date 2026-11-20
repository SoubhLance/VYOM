import csv
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

FFMPEG = r"C:\Users\Soubh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
S = pathlib.Path("backend/data/multimodal/source")
video_path = S / "lecture.mp4"
cuts_path = S / "cuts_final.csv"
out_dir = S / "_probe" / "lines"
out_dir.mkdir(parents=True, exist_ok=True)

targets = [
    (1, [20, 21, 22, 23]),
    (4, [24, 25, 26]),
    (6, [22, 23, 24, 25])
]

# Read cuts_final
cuts = {}
with open(cuts_path, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        ch = int(r['chapter'])
        sl = int(r['verse'])
        st = float(r['start'])
        en = float(r['end'])
        cuts[(ch, sl)] = (st, en)

extracted = []
for ch, slides in targets:
    for sl in slides:
        st, en = cuts[(ch, sl)]
        t_start = round(st + 3.0, 3)
        t_end = round(en - 1.0, 3)
        
        name_start = f"ch{ch:02d}_slide{sl:03d}_start.png"
        name_end = f"ch{ch:02d}_slide{sl:03d}_end.png"
        
        path_start = out_dir / name_start
        path_end = out_dir / name_end
        
        # Extract start frame
        cmd_start = [
            FFMPEG, "-ss", str(t_start), "-i", str(video_path),
            "-frames:v", "1", "-y", str(path_start)
        ]
        res_s = subprocess.run(cmd_start, capture_output=True, text=True)
        if res_s.returncode != 0:
            print(f"Error extracting {name_start}: {res_s.stderr}")
            
        # Extract end frame
        cmd_end = [
            FFMPEG, "-ss", str(t_end), "-i", str(video_path),
            "-frames:v", "1", "-y", str(path_end)
        ]
        res_e = subprocess.run(cmd_end, capture_output=True, text=True)
        if res_e.returncode != 0:
            print(f"Error extracting {name_end}: {res_e.stderr}")
            
        extracted.append((ch, sl, "start", t_start, path_start))
        extracted.append((ch, sl, "end", t_end, path_end))
        print(f"Ch {ch:02d} Slide {sl:03d}: start={st:.3f}s, end={en:.3f}s")
        print(f"  -> {name_start} at {t_start:.3f}s (size: {path_start.stat().st_size} bytes)")
        print(f"  -> {name_end} at {t_end:.3f}s (size: {path_end.stat().st_size} bytes)")

print(f"\nTotal extracted frames: {len(extracted)} (expected 22)")

