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
corrections_path = S / 'corrections.json'
out_path = S / 'vyom_clips_v3.json'

# Load corrections
with open(corrections_path, encoding='utf-8') as f:
    corrections = json.load(f)

# Load manifest
with open(manifest_path, encoding='utf-8') as f:
    manifest = json.load(f)

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
gita_verses = {}
for ch in range(1, 19):
    ch_path = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
    if not ch_path.exists():
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

# Pre-normalize verses: text_raw (before corrections) and text_corr (after corrections)
verse_norm_raw = {}
verse_norm_corr = {}
correction_matches = {i: 0 for i in range(len(corrections))}

for ch in range(1, 19):
    for vn, v in gita_verses[ch].items():
        raw_lines = clean_verse_lines(v['text'])
        verse_norm_raw[(ch, vn)] = raw_lines
        
        corr_lines = list(raw_lines)
        for i, corr in enumerate(corrections):
            if corr['chapter'] == ch and corr['verse'] == vn:
                for l_idx in range(len(corr_lines)):
                    if corr['old'] in corr_lines[l_idx]:
                        corr_lines[l_idx] = corr_lines[l_idx].replace(corr['old'], corr['new'])
                        correction_matches[i] += 1
                        
        verse_norm_corr[(ch, vn)] = corr_lines

# Assert every correction matched exactly once across normalized verse lines
for i, corr in enumerate(corrections):
    assert correction_matches[i] == 1, (
        f"Correction {corr} matched {correction_matches[i]} times in normalized verse lines (expected 1)"
    )

# Precompute shifted block normalized lines (using corrected lines)
# Block 1: ch1 verses 26-37
ch1_block_lines = []
for vn in range(26, 38):
    ch1_block_lines.extend(verse_norm_corr[(1, vn)])
assert len(ch1_block_lines) == 24, f"Expected 24 lines, got {len(ch1_block_lines)}"

# Block 2: ch4 verses 29-31
ch4_block_lines = []
for vn in range(29, 32):
    ch4_block_lines.extend(verse_norm_corr[(4, vn)])
assert len(ch4_block_lines) == 6, f"Expected 6 lines, got {len(ch4_block_lines)}"

# Map slices for shifted blocks
ch1_slide_slices = {}
ch1_slide_slices[26] = ch1_block_lines[0:3]
for s_idx in range(27, 36):
    start_i = 3 + (s_idx - 27) * 2
    end_i = start_i + 2
    ch1_slide_slices[s_idx] = ch1_block_lines[start_i:end_i]
ch1_slide_slices[36] = ch1_block_lines[21:24]

ch4_slide_slices = {
    29: ch4_block_lines[0:3],
    30: ch4_block_lines[3:5],
    31: ch4_block_lines[5:6]
}

# Verify block lines are used exactly once
ch1_reconstructed = []
for s_idx in range(26, 37):
    ch1_reconstructed.extend(ch1_slide_slices[s_idx])
assert ch1_reconstructed == ch1_block_lines
assert len(ch1_reconstructed) == len(ch1_block_lines) == 24

ch4_reconstructed = []
for s_idx in range(29, 32):
    ch4_reconstructed.extend(ch4_slide_slices[s_idx])
assert ch4_reconstructed == ch4_block_lines
assert len(ch4_reconstructed) == len(ch4_block_lines) == 6

vyom_clips = []
missing_audio = []
missing_text = []

for i in range(len(cuts_rows)):
    c_row = cuts_rows[i]
    m_row = slide_map_rows[i]
    
    ch = int(c_row['chapter'])
    sl = int(c_row['verse'])
    
    assert ch == int(m_row['chapter'])
    assert sl == int(m_row['slide'])
    
    m_entry = manifest_by_cv.get((ch, sl))
    if not m_entry:
        sys.exit(f"Missing manifest entry for Ch {ch} Slide {sl}")
        
    audio_rel = m_entry['audio']
    audio_full = S / 'assets' / audio_rel
    if not audio_full.exists():
        missing_audio.append((ch, sl, audio_rel))
        
    clip_id = pathlib.Path(audio_rel).stem
    st = float(c_row['start'])
    en = float(c_row['end'])
    dur = round(en - st, 3)
    
    dv_list = [int(x) for x in m_row['data_verses'].split(';') if x.strip()]
    partial = (len(dv_list) == 2)
    
    # Speaker determination:
    # Rule: ch1 slide 27: speaker = null (the on-screen label first appears on slide 28)
    if ch == 1 and sl == 27:
        found_speaker = None
    else:
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
                
    # Build text_raw and text
    text_raw_entries = []
    text_entries = []
    for vn in dv_list:
        if (ch, vn) not in verse_norm_raw:
            missing_text.append((ch, sl, vn))
            continue
        text_raw_entries.append({
            'verse': vn,
            'lines': verse_norm_raw[(ch, vn)]
        })
        text_entries.append({
            'verse': vn,
            'lines': verse_norm_corr[(ch, vn)]
        })
        
    # spoken_lines assignment
    if ch == 1 and 26 <= sl <= 36:
        spoken_lines = ch1_slide_slices[sl]
    elif ch == 4 and 29 <= sl <= 31:
        spoken_lines = ch4_slide_slices[sl]
    else:
        spoken_lines = list(text_entries[0]['lines'])
        
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
        'text_raw': text_raw_entries,
        'text': text_entries,
        'spoken_lines': spoken_lines
    }
    vyom_clips.append(clip_entry)

# Assert each correction's new string matched in spoken_lines exactly once across all 700 clips
for i, corr in enumerate(corrections):
    count_in_spoken = 0
    for c in vyom_clips:
        for line in c['spoken_lines']:
            if corr['new'] in line:
                count_in_spoken += 1
    assert count_in_spoken == 1, (
        f"Expected correction {corr['new']} to appear once in spoken_lines, found {count_in_spoken}"
    )

# Write S/vyom_clips_v3.json
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(vyom_clips, f, ensure_ascii=False, indent=2)

print(f"Successfully wrote {out_path}: {len(vyom_clips)} entries.")

