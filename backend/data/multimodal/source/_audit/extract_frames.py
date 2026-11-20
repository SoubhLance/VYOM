import csv, subprocess, os, sys, pathlib

S = pathlib.Path('backend/data/multimodal/source')
audit = S / '_audit' / 'frames'
video = str(S / 'lecture.mp4')
ffmpeg = r'C:\Users\Soubh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe'

# Build combined plan: ch1 from cuts_ch01_46.csv, ch2-18 from cuts_slides.csv
rows = []
with open(S / 'cuts_ch01_46.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)
with open(S / 'cuts_slides.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        if int(r['chapter']) >= 2:
            rows.append(r)

print(f"Total slides to extract: {len(rows)}")
count = 0
errors = 0
for r in rows:
    ch = int(r['chapter'])
    v = int(r['verse'])
    end = float(r['end'])
    t = end - 1.0  # extract at slide_end - 1.0s
    if t < 0:
        t = float(r['start']) + 0.5
    
    ch_dir = audit / f'ch{ch:02d}'
    ch_dir.mkdir(parents=True, exist_ok=True)
    out = ch_dir / f'slide{v:03d}.png'
    
    if out.exists():
        count += 1
        continue
    
    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error',
           '-ss', str(t), '-i', video,
           '-vf', 'crop=iw*0.68:ih*0.42:iw*0.25:ih*0.08,scale=640:-1',
           '-frames:v', '1', '-y', str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"ERROR ch{ch} v{v}: {result.stderr.strip()}", file=sys.stderr)
        errors += 1
    else:
        count += 1
    
    if count % 50 == 0:
        print(f"  extracted {count}/{len(rows)}...")

print(f"Done: {count} extracted, {errors} errors out of {len(rows)} total")
