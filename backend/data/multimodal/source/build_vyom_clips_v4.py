import csv
import json
import pathlib
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
manifest_path = S / 'assets' / 'manifest.json'
cuts_path = S / 'cuts_final.csv'
slide_map_path = S / 'slide_map_v2.csv'
corrections_path = S / 'corrections.json'
out_path = S / 'vyom_clips_v4.json'

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

# Load slide_map_v2
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

# Recognized speaker patterns (now accepting संजय उवाच as well)
speaker_patterns = [
    'श्री भगवानुवाच',
    'श्रीभगवानुवाच',
    'भगवानुवाच',
    'अर्जुन उवाच',
    'सञ्जय उवाच',
    'संजय उवाच',
    'धृतराष्ट्र उवाच'
]

def parse_canonical_speaker(sp):
    if not sp:
        return None
    if 'भगवानुवाच' in sp:
        return 'श्रीभगवानुवाच'
    elif 'संजय उवाच' in sp or 'सञ्जय उवाच' in sp:
        return 'सञ्जय उवाच'
    elif 'अर्जुन उवाच' in sp:
        return 'अर्जुन उवाच'
    elif 'धृतराष्ट्र उवाच' in sp:
        return 'धृतराष्ट्र उवाच'
    return sp

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

def make_search_text(lines):
    if isinstance(lines, list):
        t = " ".join(lines)
    else:
        t = str(lines)
        
    # 1. NFC normalization
    t = unicodedata.normalize('NFC', t)
    
    # 2. remove U+093C (nukta)
    t = t.replace('\u093c', '')
    
    # 3. remove ZWJ and ZWNJ
    t = t.replace('\u200d', '').replace('\u200c', '')
    
    # 4. remove avagraha (ऽ, \u093d)
    t = t.replace('ऽ', '').replace('\u093d', '')
    
    # 5. replace श्रृ with शृ
    t = t.replace('श्रृ', 'शृ')
    
    # 6. replace anusvara/class-nasal+halant variants with ं
    t = re.sub(r'ङ्([कखगघङ])', r'ं\1', t)
    t = re.sub(r'ञ्([चछजझञ])', r'ं\1', t)
    t = re.sub(r'ण्([टठडढण])', r'ं\1', t)
    t = re.sub(r'न्([तथदधन])', r'ं\1', t)
    t = re.sub(r'म्([पफबभम])', r'ं\1', t)
    
    # 7. collapse whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t

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

# ----------------- SHIFTED BLOCKS SETUP -----------------

# 1. Block ch1 verses 20-22 (6 lines):
# slide 20 = lines[0:3], slide 21 = lines[3:5], slide 22 = lines[5:6]
ch1_b1_lines = []
for vn in range(20, 23):
    ch1_b1_lines.extend(verse_norm_corr[(1, vn)])
assert len(ch1_b1_lines) == 6, f"Expected 6 lines, got {len(ch1_b1_lines)}"
ch1_b1_slices = {
    20: ch1_b1_lines[0:3],
    21: ch1_b1_lines[3:5],
    22: ch1_b1_lines[5:6]
}
assert ch1_b1_slices[20] + ch1_b1_slices[21] + ch1_b1_slices[22] == ch1_b1_lines

# 2. Block ch1 verses 26-37 (24 lines):
# slide 26 = lines[0:3], slides 27..35 = 2 lines each, slide 36 = lines[21:24]
ch1_b2_lines = []
for vn in range(26, 38):
    ch1_b2_lines.extend(verse_norm_corr[(1, vn)])
assert len(ch1_b2_lines) == 24, f"Expected 24 lines, got {len(ch1_b2_lines)}"
ch1_b2_slices = {}
ch1_b2_slices[26] = ch1_b2_lines[0:3]
for s_idx in range(27, 36):
    start_i = 3 + (s_idx - 27) * 2
    end_i = start_i + 2
    ch1_b2_slices[s_idx] = ch1_b2_lines[start_i:end_i]
ch1_b2_slices[36] = ch1_b2_lines[21:24]
ch1_b2_recon = []
for s_idx in range(26, 37):
    ch1_b2_recon.extend(ch1_b2_slices[s_idx])
assert ch1_b2_recon == ch1_b2_lines

# 3. Block ch4 verses 29-31 (6 lines):
# slide 29 = lines[0:3], slide 30 = lines[3:5], slide 31 = lines[5:6]
ch4_b_lines = []
for vn in range(29, 32):
    ch4_b_lines.extend(verse_norm_corr[(4, vn)])
assert len(ch4_b_lines) == 6, f"Expected 6 lines, got {len(ch4_b_lines)}"
ch4_b_slices = {
    29: ch4_b_lines[0:3],
    30: ch4_b_lines[3:5],
    31: ch4_b_lines[5:6]
}
assert ch4_b_slices[29] + ch4_b_slices[30] + ch4_b_slices[31] == ch4_b_lines

# 4. Block ch6 verses 23-24 (4 lines):
# slide 23 = lines[0:1], slide 24 = lines[1:4]
ch6_b_lines = []
for vn in range(23, 25):
    ch6_b_lines.extend(verse_norm_corr[(6, vn)])
assert len(ch6_b_lines) == 4, f"Expected 4 lines, got {len(ch6_b_lines)}"
ch6_b_slices = {
    23: ch6_b_lines[0:1],
    24: ch6_b_lines[1:4]
}
assert ch6_b_slices[23] + ch6_b_slices[24] == ch6_b_lines

# ----------------- BUILD ENTRIES -----------------

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
    
    # Partial flag:
    # prompt rules:
    # ch1 20-21: partial=True, 22: partial=False
    # ch6 23 and 24: partial=True for both
    # ch1 26-36: partial=True
    # ch4 29, 30: partial=True, 31: partial=False
    # all others: (len(dv_list) == 2)
    if ch == 1 and sl in [20, 21]:
        partial = True
    elif ch == 1 and sl == 22:
        partial = False
    elif ch == 6 and sl in [23, 24]:
        partial = True
    elif ch == 4 and sl == 31:
        partial = False
    else:
        partial = (len(dv_list) == 2)
        
    # Speaker determination:
    # Rule for shifted slides:
    # ch1 slide 21 = "अर्जुन उवाच", slides 20 and 22 = null
    # ch1 slide 27 = null, slide 28 = "अर्जुन उवाच", slides 26, 29..36 = null
    # ch4 slides 29..31 = null
    # ch6 slides 23..24 = null
    if ch == 1 and sl in [20, 22]:
        found_speaker = None
    elif ch == 1 and sl == 21:
        found_speaker = 'अर्जुन उवाच'
    elif ch == 1 and sl == 27:
        found_speaker = None
    elif ch == 1 and 26 <= sl <= 36 and sl != 28:
        found_speaker = None
    elif ch == 1 and sl == 28:
        found_speaker = 'अर्जुन उवाच'
    elif ch == 4 and 29 <= sl <= 31:
        found_speaker = None
    elif ch == 6 and sl in [23, 24]:
        found_speaker = None
    else:
        # Standard speaker detection from mapped data verses
        found_speaker = None
        for vn in dv_list:
            v = gita_verses[ch].get(vn)
            if not v:
                continue
            v_raw = v['text']
            for sp in speaker_patterns:
                if sp in v_raw:
                    found_speaker = parse_canonical_speaker(sp)
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
            'lines': verse_norm_raw[(ch, vn)] # original uncollapsed lines
        })
        # Collapse runs of whitespace in text lines
        text_entries.append({
            'verse': vn,
            'lines': [re.sub(r'\s+', ' ', l).strip() for l in verse_norm_corr[(ch, vn)]]
        })
        
    # Spoken lines assignment:
    if ch == 1 and 20 <= sl <= 22:
        raw_spoken = ch1_b1_slices[sl]
    elif ch == 1 and 26 <= sl <= 36:
        raw_spoken = ch1_b2_slices[sl]
    elif ch == 4 and 29 <= sl <= 31:
        raw_spoken = ch4_b_slices[sl]
    elif ch == 6 and 23 <= sl <= 24:
        raw_spoken = ch6_b_slices[sl]
    else:
        raw_spoken = verse_norm_corr[(ch, dv_list[0])]
        
    # Collapse runs of whitespace in spoken_lines
    spoken_lines = [re.sub(r'\s+', ' ', l).strip() for l in raw_spoken]
    
    # Generate search_text
    search_text = make_search_text(spoken_lines)
    
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
        'spoken_lines': spoken_lines,
        'search_text': search_text
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

# Write S/vyom_clips_v4.json
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(vyom_clips, f, ensure_ascii=False, indent=2)

print(f"Successfully wrote {out_path}: {len(vyom_clips)} entries.")

