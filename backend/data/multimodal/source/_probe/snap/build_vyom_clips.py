import csv
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
manifest_path = S / 'assets' / 'manifest.json'
cuts_path = S / 'cuts_final.csv'
slide_map_path = S / 'slide_map.csv'
out_path = S / 'vyom_clips.json'

# Load manifest
with open(manifest_path, encoding='utf-8') as f:
    manifest = json.load(f)

# Build manifest lookup by (chapter, slide/verse)
manifest_by_cv = {}
for vid, entry in manifest.items():
    manifest_by_cv[(int(entry['chapter']), int(entry['verse']))] = entry

# Load cuts_final
cuts_rows = []
with open(cuts_path, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        cuts_rows.append(r)

# Load slide_map
slide_map_rows = []
with open(slide_map_path, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        slide_map_rows.append(r)

# Load all chapter verses
# Notice folders are unpadded integers 1..18
gita_verses = {}
for ch in range(1, 19):
    ch_path = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
    if not ch_path.exists():
        # try padded
        ch_path = pathlib.Path(f'backend/data/gita/{ch:02d}/verses.json')
    with open(ch_path, encoding='utf-8') as f:
        verses = json.load(f)
    gita_verses[ch] = {int(v['verse_number']): v for v in verses}

speaker_patterns = [
    'श्री भगवानुवाच',
    'श्रीभगवानुवाच',
    'भगवानुवाच',
    'अर्जुन उवाच',
    'सञ्जय उवाच',
    'धृतराष्ट्र उवाच'
]

def clean_verse_lines(raw_text):
    # 1. strip U+093C
    t = raw_text.replace('\u093c', '')
    
    # 2. remove speaker label
    for sp in speaker_patterns:
        if sp in t:
            t = t.replace(sp, '')
            
    # 3. remove trailing ।।C.V।। marker
    t = re.sub(r'[।|॥]+\s*\d+\.\d+\s*[।|॥]+\s*$', '', t.strip())
    
    # 4. split on । (drop empty strings)
    parts = t.split('।')
    lines = [p.strip() for p in parts if p.strip()]
    return lines

vyom_clips = []
missing_audio = []
missing_text = []
non_two_lines = []

for i in range(len(cuts_rows)):
    c_row = cuts_rows[i]
    m_row = slide_map_rows[i]
    
    ch = int(c_row['chapter'])
    sl = int(c_row['verse']) # slide index
    
    assert ch == int(m_row['chapter'])
    assert sl == int(m_row['slide'])
    
    m_entry = manifest_by_cv.get((ch, sl))
    if not m_entry:
        sys.exit(f"Missing manifest entry for Ch {ch} Slide {sl}")
        
    audio_rel = m_entry['audio']
    audio_full = S / 'assets' / audio_rel
    if not audio_full.exists():
        missing_audio.append((ch, sl, audio_rel))
        
    clip_id = pathlib.Path(audio_rel).stem # e.g. bg_04_29
    st = float(c_row['start'])
    en = float(c_row['end'])
    dur = round(en - st, 3)
    
    dv_list = [int(x) for x in m_row['data_verses'].split(';') if x.strip()]
    partial = (len(dv_list) == 2)
    
    # Determine speaker
    found_speaker = None
    for vn in dv_list:
        v = gita_verses[ch].get(vn)
        if not v:
            continue
        v_raw = v['text']
        for sp in speaker_patterns:
            if sp in v_raw:
                if 'भगवानुवाच' in sp:
                    found_speaker = 'श्रीभगवानुवाच'
                else:
                    found_speaker = sp
                break
        if found_speaker:
            break
            
    # Extract text entries per data verse
    text_entries = []
    for vn in dv_list:
        v = gita_verses[ch].get(vn)
        if not v:
            missing_text.append((ch, sl, vn))
            continue
        lines = clean_verse_lines(v['text'])
        if len(lines) != 2:
            non_two_lines.append((ch, vn, lines))
        text_entries.append({
            'verse': vn,
            'lines': lines
        })
        
    clip_entry = {
        'clip_id': clip_id,
        'chapter': ch,
        'slide': sl,
        'audio_path': audio_rel,
        'start': st,
        'end': en,
        'duration': dur,
        'data_verses': dv_list,
        'partial': partial,
        'speaker': found_speaker,
        'text': text_entries
    }
    vyom_clips.append(clip_entry)

# Write S/vyom_clips.json
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(vyom_clips, f, ensure_ascii=False, indent=2)

print(f"Wrote {out_path}: {len(vyom_clips)} entries.")

# Verification checks
print("\n=== 1. ENTRY COUNT & MISSING MEDIA/TEXT ===")
print(f"Total entries: {len(vyom_clips)} (expected 700)")
print(f"Clips missing audio: {len(missing_audio)}")
for ma in missing_audio:
    print(f"  Missing audio: {ma}")
print(f"Clips missing text: {len(missing_text)}")
for mt in missing_text:
    print(f"  Missing text: {mt}")

print("\n=== 2. ENTRIES WHERE SPEAKER IS NOT NULL ===")
speaker_counts = {}
for entry in vyom_clips:
    if entry['speaker'] is not None:
        c = entry['chapter']
        speaker_counts[c] = speaker_counts.get(c, 0) + 1

for ch in range(1, 19):
    print(f"  Chapter {ch:2d}: {speaker_counts.get(ch, 0):2d} clips with speaker")
print(f"Total clips with speaker: {sum(speaker_counts.values())}")

print("\n=== 3. FULL ENTRIES FOR bg_01_26, bg_04_29, bg_04_31, bg_13_01 ===")
for target_id in ['bg_01_26', 'bg_04_29', 'bg_04_31', 'bg_13_01']:
    match = next(c for c in vyom_clips if c['clip_id'] == target_id)
    print(f"\n--- Entry: {target_id} ---")
    print(json.dumps(match, ensure_ascii=False, indent=2))

print("\n=== 4. VERSES WHOSE NORMALIZED TEXT DOES NOT SPLIT INTO EXACTLY 2 LINES ===")
print(f"Total verses not splitting into exactly 2 lines: {len(non_two_lines)}")
if non_two_lines:
    print("First 10 examples:")
    for ch, vn, lns in non_two_lines[:10]:
        print(f"  Ch {ch}.{vn} ({len(lns)} lines): {lns}")
else:
    print("  All verses split cleanly into exactly 2 lines.")

