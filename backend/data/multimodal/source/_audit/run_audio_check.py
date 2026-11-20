import csv
import pathlib
import subprocess
import re
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
video = str(S / 'lecture.mp4')
ffmpeg = r'C:\Users\Soubh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe'

# Load combined plan (ch1 from cuts_ch01_46.csv, ch2-18 from cuts_slides.csv)
plan_rows = []
with open(S / 'cuts_ch01_46.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        plan_rows.append(r)
with open(S / 'cuts_slides.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if int(r['chapter']) >= 2:
            plan_rows.append(r)

ch_rows = {}
for r in plan_rows:
    ch = int(r['chapter'])
    ch_rows.setdefault(ch, []).append(r)

# Select sample of at least 10 slides per chapter:
# Must include: first (0), last (-1), every flagged one, every clip under 8s
sampled_per_ch = {}
for ch in range(1, 19):
    rows = ch_rows[ch]
    n = len(rows)
    indices = set()
    indices.add(0)
    indices.add(n - 1)
    
    for i, r in enumerate(rows):
        dur = float(r['dur_sec'])
        flags = r.get('flags', '').strip()
        if flags or dur < 8.0:
            indices.add(i)
            
    # If < 10, evenly pick across the chapter
    if len(indices) < 10:
        step = max(1, n // 12)
        for i in range(0, n, step):
            indices.add(i)
            if len(indices) >= 12:
                break
    sampled_per_ch[ch] = sorted(list(indices))

total_sampled = sum(len(v) for v in sampled_per_ch.values())
print(f"Total sampled slides across 18 chapters: {total_sampled}")

results = []
chapter_start_offsets = {}
chapter_end_offsets = {}

for ch in range(1, 19):
    chapter_start_offsets[ch] = []
    chapter_end_offsets[ch] = []
    rows = ch_rows[ch]
    for idx in sampled_per_ch[ch]:
        r = rows[idx]
        v = int(r.get('verse', r.get('slide', idx + 1)))
        st = float(r['start'])
        en = float(r['end'])
        dur = float(r['dur_sec'])
        flags = r.get('flags', '')
        
        w_st = max(0.0, st - 2.0)
        w_en = en + 2.0
        w_len = w_en - w_st
        
        slide_st_rel = st - w_st
        slide_en_rel = en - w_st
        
        cmd = [
            ffmpeg, '-hide_banner', '-loglevel', 'info',
            '-ss', f"{w_st:.3f}", '-to', f"{w_en:.3f}",
            '-i', video, '-vn',
            '-af', 'silencedetect=noise=-35dB:d=0.2',
            '-f', 'null', '-'
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        stderr = res.stderr
        
        # Parse silences
        silences = []
        cur_sil_st = None
        for line in stderr.splitlines():
            m_st = re.search(r'silence_start:\s*([\d.]+)', line)
            if m_st:
                cur_sil_st = float(m_st.group(1))
            m_en = re.search(r'silence_end:\s*([\d.]+)', line)
            if m_en and cur_sil_st is not None:
                silences.append((cur_sil_st, float(m_en.group(1))))
                cur_sil_st = None
        if cur_sil_st is not None:
            silences.append((cur_sil_st, w_len))
            
        # Invert silences to get speech intervals within [0, w_len]
        speech = []
        pos = 0.0
        for s_st, s_en in silences:
            if s_st > pos + 0.02:
                speech.append((pos, s_st))
            pos = max(pos, s_en)
        if pos < w_len - 0.02:
            speech.append((pos, w_len))
            
        # Analyze speech relative to slide_st_rel and slide_en_rel
        # 1. Speech near start:
        # Look for speech active at or starting around slide_st_rel
        # Specifically, speech segments that overlap [0, slide_st_rel + 1.0]
        st_offset = None
        begins_before = False
        
        # Check if speech is active at slide_st_rel
        for sp_st, sp_en in speech:
            if sp_st <= slide_st_rel <= sp_en:
                # Speech is actively continuing across the slide transition
                st_offset = -(slide_st_rel - sp_st) # negative: speech started before slide change
                begins_before = True
                break
            elif sp_st > slide_st_rel:
                # Speech starts after slide transition
                st_offset = sp_st - slide_st_rel
                break
                
        if st_offset is None and speech:
            # All speech ended before slide start
            st_offset = speech[0][0] - slide_st_rel
            
        # 2. Speech near end:
        en_offset = None
        bleed_next = False
        
        for sp_st, sp_en in reversed(speech):
            if sp_st <= slide_en_rel <= sp_en:
                # Speech continues past slide end!
                en_offset = -(sp_en - slide_en_rel) # negative: speech extends past end
                bleed_next = True
                break
            elif sp_en < slide_en_rel:
                # Speech ended before slide end
                en_offset = slide_en_rel - sp_en
                break
                
        if en_offset is None and speech:
            en_offset = slide_en_rel - speech[-1][1]
            
        if st_offset is not None:
            chapter_start_offsets[ch].append(st_offset)
        if en_offset is not None:
            chapter_end_offsets[ch].append(en_offset)
            
        results.append({
            'chapter': ch, 'verse': v, 'start': st, 'end': en, 'dur': dur,
            'st_offset': st_offset, 'begins_before': begins_before,
            'en_offset': en_offset, 'bleed_next': bleed_next,
            'flags': flags
        })

print("\n=== AUDIO BOUNDARY ANALYSIS SUMMARY ===")
print("Ch | Samples | Med Start Off (s) | Spread (s) | Med End Off (s) | Spread (s) | Bleed Count | Before Count")
all_st_offsets = []
for ch in range(1, 19):
    st_offs = chapter_start_offsets[ch]
    en_offs = chapter_end_offsets[ch]
    all_st_offsets.extend(st_offs)
    med_st = np.median(st_offs) if st_offs else 0.0
    iqr_st = (np.percentile(st_offs, 75) - np.percentile(st_offs, 25)) if st_offs else 0.0
    med_en = np.median(en_offs) if en_offs else 0.0
    iqr_en = (np.percentile(en_offs, 75) - np.percentile(en_offs, 25)) if en_offs else 0.0
    ch_results = [r for r in results if r['chapter'] == ch]
    bleed_cnt = sum(1 for r in ch_results if r['bleed_next'])
    before_cnt = sum(1 for r in ch_results if r['begins_before'])
    print(f"{ch:2d} | {len(ch_results):7d} | {med_st:17.3f} | {iqr_st:10.3f} | {med_en:15.3f} | {iqr_en:10.3f} | {bleed_cnt:11d} | {before_cnt:12d}")

overall_med_st = np.median(all_st_offsets)
overall_std_st = np.std(all_st_offsets)
print(f"\nOverall Median Start Offset: {overall_med_st:.3f} s (std: {overall_std_st:.3f} s)")

# Save full results to _audit/audio_boundary_report.csv
out_csv = S / '_audit' / 'audio_boundary_report.csv'
with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['chapter', 'verse', 'start', 'end', 'dur', 'st_offset', 'begins_before', 'en_offset', 'bleed_next', 'flags'])
    writer.writeheader()
    writer.writerows(results)
print(f"Saved detailed audio report to {out_csv}")

# Identify 12 specific clips for human listening test:
# Prioritize: clips where speech begins before start (or very small st_offset < 0.2s),
# flagged clips, and short clips where clipping risk is highest.
high_risk = [r for r in results if r['begins_before'] or (r['st_offset'] is not None and r['st_offset'] < 0.15)]
if len(high_risk) < 12:
    # add clips with smallest st_offset
    sorted_by_st = sorted(results, key=lambda x: (x['st_offset'] if x['st_offset'] is not None else 999))
    for r in sorted_by_st:
        if r not in high_risk:
            high_risk.append(r)
        if len(high_risk) >= 12:
            break

print("\n=== 12 SPECIFIC CLIPS FOR HUMAN LISTENING (FIRST-SYLLABLE CLIPPING RISK) ===")
print("No | Chapter | Verse | Start (s) | End (s) | Dur (s) | Start Offset (s) | Issue / Reason")
for i, r in enumerate(high_risk[:12], 1):
    reason = "Speech begins BEFORE slide cut" if r['begins_before'] else f"Very tight start margin ({r['st_offset']:.2f}s)"
    if r['flags']:
        reason += f" [{r['flags']}]"
    print(f"{i:2d} | Ch {r['chapter']:2d}   | V {r['verse']:3d}  | {r['start']:9.3f} | {r['end']:9.3f} | {r['dur']:5.1f} | {r['st_offset']:16.3f} | {reason}")

