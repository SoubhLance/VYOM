import csv
import json
import pathlib
import subprocess
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
audit = S / '_audit'
video = S / 'lecture.mp4'
ffprobe = r'C:\Users\Soubh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe'

print("=== CHECK A.1: ffprobe duration & chapters.csv ===")
cmd = [ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(video)]
res = subprocess.run(cmd, capture_output=True, text=True)
duration = float(res.stdout.strip())
print(f"lecture.mp4 ffprobe duration: {duration:.3f} s ({duration/3600:.4f} h)")

chapters = []
with open(S / 'chapters.csv', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for r in reader:
        parts = r['start'].strip().split(':')
        if len(parts) == 2:
            sec = int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        else:
            sec = float(parts[0])
        chapters.append((int(r['chapter']), r['start'].strip(), sec))

print(f"chapters.csv rows: {len(chapters)}")
increasing = all(chapters[i][2] < chapters[i+1][2] for i in range(len(chapters)-1))
print(f"Chapters strictly increasing: {increasing}")
for ch, st_str, st_sec in chapters:
    print(f"  Ch {ch:2d}: {st_str:8s} -> {st_sec:8.1f} s")

print("\n=== CHECK A.2: Combined Plan Integrity (cuts_ch01_46.csv + cuts_slides.csv ch02-18) ===")
expected_counts = {
    1: 46, 2: 72, 3: 43, 4: 42, 5: 29, 6: 47, 7: 30, 8: 28, 9: 34,
    10: 42, 11: 55, 12: 20, 13: 35, 14: 27, 15: 20, 16: 24, 17: 28, 18: 78
}

plan_rows = []
with open(S / 'cuts_ch01_46.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        plan_rows.append(r)
with open(S / 'cuts_slides.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if int(r['chapter']) >= 2:
            plan_rows.append(r)

print(f"Total plan rows: {len(plan_rows)}")
ch_rows = {}
for r in plan_rows:
    ch = int(r['chapter'])
    ch_rows.setdefault(ch, []).append(r)

for ch in range(1, 19):
    cnt = len(ch_rows.get(ch, []))
    exp = expected_counts[ch]
    match_str = "OK" if cnt == exp else f"MISMATCH (expected {exp})"
    print(f"  Ch {ch:2d}: {cnt} rows vs expected {exp} -> {match_str}")

ch_windows = {}
for i in range(len(chapters)):
    c_num = chapters[i][0]
    c_start = chapters[i][2]
    c_end = chapters[i+1][2] if i+1 < len(chapters) else duration
    ch_windows[c_num] = (c_start, c_end)

under_3s = []
over_30s = []
overlaps = []
neg_dur = []
window_violations = []

for ch in range(1, 19):
    rows = ch_rows[ch]
    c_win_start, c_win_end = ch_windows[ch]
    for i in range(len(rows)):
        r = rows[i]
        st = float(r['start'])
        en = float(r['end'])
        dur = en - st
        v = int(r.get('verse', r.get('slide', i+1)))
        
        if dur <= 0:
            neg_dur.append((ch, v, st, en, dur))
        if dur < 3.0:
            under_3s.append((ch, v, st, en, dur))
        if dur > 30.0:
            over_30s.append((ch, v, st, en, dur))
        
        if st < c_win_start - 0.5 or en > c_win_end + 0.5:
            window_violations.append((ch, v, st, en, c_win_start, c_win_end))
        
        if i > 0:
            prev_en = float(rows[i-1]['end'])
            prev_st = float(rows[i-1]['start'])
            if st < prev_en - 0.001:
                overlaps.append((ch, v, prev_en, st))
            if st <= prev_st:
                print(f"  WARNING: Ch {ch} v {v} start <= prev start: {st} <= {prev_st}")

print(f"Negative durations: {len(neg_dur)}")
print(f"Overlaps between clips: {len(overlaps)}")
print(f"Chapter window violations: {len(window_violations)}")
print(f"Clips under 3s: {len(under_3s)}")
for x in under_3s:
    print(f"  UNDER 3s: Ch {x[0]} slide {x[1]}: start={x[2]:.3f}, end={x[3]:.3f}, dur={x[4]:.3f}s")
print(f"Clips over 30s: {len(over_30s)}")
for x in over_30s:
    print(f"  OVER 30s: Ch {x[0]} slide {x[1]}: start={x[2]:.3f}, end={x[3]:.3f}, dur={x[4]:.3f}s")

print("\n=== CHECK A.3: scene_chNN.txt vs Planned Clips & Dropped Changes ===")
probe_dir = S / '_probe'
for ch in range(1, 19):
    sc_file = probe_dir / f'scene_ch{ch:02d}.txt'
    with open(sc_file) as f:
        changes = [float(line.strip()) for line in f if line.strip()]
    num_changes = len(changes)
    num_planned = len(ch_rows[ch])
    first_planned_st = float(ch_rows[ch][0]['start'])
    first_planned_en = float(ch_rows[ch][0]['end'])
    last_planned_st = float(ch_rows[ch][-1]['start'])
    last_planned_en = float(ch_rows[ch][-1]['end'])
    
    diff = num_changes - num_planned
    head_dropped = [c for c in changes if c < first_planned_st - 0.1]
    tail_dropped = [c for c in changes if c > last_planned_en + 0.1]
    print(f"Ch {ch:02d}: {num_changes} changes, {num_planned} planned clips (diff: {diff:+d}) | head dropped: {len(head_dropped)} ({[round(x,3) for x in head_dropped]}), tail dropped: {len(tail_dropped)} ({[round(x,3) for x in tail_dropped]})")

print("\n=== CHECK B.4: Data Verse Counts per Chapter (backend/data/gita) ===")
data_counts = {}
verse_gaps_dups = {}
expected_data_counts = {
    1: 47, 2: 72, 3: 43, 4: 42, 5: 29, 6: 47, 7: 30, 8: 28, 9: 34,
    10: 42, 11: 55, 12: 20, 13: 35, 14: 27, 15: 20, 16: 24, 17: 28, 18: 78
}

for ch in range(1, 19):
    v_file = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
    with open(v_file, encoding='utf-8') as f:
        v_data = json.load(f)
    data_counts[ch] = len(v_data)
    v_nums = [int(x['verse_number']) for x in v_data]
    
    seen = set()
    dups = []
    for num in v_nums:
        if num in seen:
            dups.append(num)
        seen.add(num)
    
    expected_v_set = set(range(1, expected_data_counts[ch] + 1))
    gaps = expected_v_set - seen
    
    status = "OK" if len(v_data) == expected_data_counts[ch] and not dups and not gaps else "ANOMALY"
    print(f"Ch {ch:02d}: {len(v_data)} verses vs exp {expected_data_counts[ch]} | dups: {dups} | gaps: {sorted(list(gaps))} -> {status}")

print("\n=== CHECK B.5: Data Hygiene Anomalies (U+093C, glued speaker labels, line breaks, length) ===")
nukta_verses = []
glued_speaker_verses = []
missing_linebreak_verses = []
short_verses = []

speaker_labels = ['धृतराष्ट्र उवाच', 'सञ्जय उवाच', 'अर्जुन उवाच', 'श्रीभगवानुवाच', 'श्री भगवानुवाच', 'भगवानुवाच']

for ch in range(1, 19):
    v_file = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
    with open(v_file, encoding='utf-8') as f:
        v_data = json.load(f)
    for x in v_data:
        v_num = x['verse_number']
        raw_text = x.get('text', [])
        if isinstance(raw_text, list):
            joined_text = "\n".join(raw_text)
            lines = [l.strip() for l in raw_text if l.strip()]
        else:
            joined_text = str(raw_text)
            lines = [l.strip() for l in joined_text.splitlines() if l.strip()]
        
        ref = f"Ch {ch}.{v_num}"
        
        if '\u093c' in joined_text:
            nukta_verses.append((ref, joined_text))
            
        glued_found = False
        for sp in speaker_labels:
            pattern = re.escape(sp) + r'[^\s\n\r।॥]'
            if re.search(pattern, joined_text):
                glued_speaker_verses.append((ref, joined_text))
                glued_found = True
                break
            for l in lines:
                if l.startswith(sp) and len(l) > len(sp) + 2:
                    rest = l[len(sp):].strip()
                    if rest and not rest.startswith(('।', '॥')):
                        if not glued_found:
                            glued_speaker_verses.append((ref, l))
                            glued_found = True
                            break
                            
        verse_lines_only = [l for l in lines if not any(l == sp or l == sp.replace(' ', '') for sp in speaker_labels)]
        if len(verse_lines_only) == 1 and ('।' in verse_lines_only[0] or '॥' in verse_lines_only[0]):
            missing_linebreak_verses.append((ref, verse_lines_only[0]))
        elif len(verse_lines_only) == 0:
            short_verses.append((ref, joined_text))
            
        clean_len = len("".join(verse_lines_only).strip())
        if clean_len < 20:
            short_verses.append((ref, joined_text, clean_len))

print(f"Total verses with U+093C (nukta): {len(nukta_verses)}")
print("First 5 examples:")
for ref, txt in nukta_verses[:5]:
    matches = re.findall(r'.{0,5}\u093c.{0,5}', txt)
    print(f"  {ref}: {matches} in {txt[:60]}...")

print(f"\nTotal verses with glued speaker labels: {len(glued_speaker_verses)}")
print("First 5 examples:")
for ref, txt in glued_speaker_verses[:5]:
    print(f"  {ref}: {txt[:80]}...")

print(f"\nTotal verses missing line break between lines: {len(missing_linebreak_verses)}")
print("First 5 examples:")
for ref, txt in missing_linebreak_verses[:5]:
    print(f"  {ref}: {txt[:80]}...")

print(f"\nTotal verses empty or short (<20 chars): {len(short_verses)}")
for x in short_verses:
    print(f"  {x}")
