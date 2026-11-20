import csv
import json
import pathlib
import re
import difflib
import sys

sys.stdout.reconfigure(encoding='utf-8')

S = pathlib.Path('backend/data/multimodal/source')
audit_dir = S / '_audit'
ocr_csv = audit_dir / 'ocr_blind.csv'
alignment_csv = audit_dir / 'alignment_report.csv'

# Load combined cuts to get start/end times
cuts_rows = {}
with open(S / 'cuts_ch01_46.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        ch = int(r['chapter'])
        sl = int(r['verse'])
        cuts_rows[(ch, sl)] = (float(r['start']), float(r['end']), float(r['dur_sec']))

with open(S / 'cuts_slides.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        ch = int(r['chapter'])
        if ch >= 2:
            sl = int(r['verse'])
            cuts_rows[(ch, sl)] = (float(r['start']), float(r['end']), float(r['dur_sec']))

# Load all data verses
data_verses = {}
for ch in range(1, 19):
    v_path = pathlib.Path(f'backend/data/gita/{ch}/verses.json')
    with open(v_path, encoding='utf-8') as f:
        data_verses[ch] = json.load(f)

def normalize_deva(text):
    if not text:
        return ""
    text = text.replace('\u093c', '')
    for sp in [
        'धृतराष्ट्र उवाच', 'सञ्जय उवाच', 'अर्जुन उवाच', 'श्रीभगवानुवाच', 'श्री भगवानुवाच', 'भगवानुवाच',
        'घृतराष्र उवाच', 'सब्नय उवाच', 'सञ्चय उवाच'
    ]:
        text = text.replace(sp, '')
    text = re.sub(r'[\s\d०-९।॥|:!?.—\-+=,/\\\'"()\[\]{}*#<>;_`~^]+', '', text)
    return text

def sim(s1, s2):
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()

# Load blind OCR rows
ocr_rows = []
with open(ocr_csv, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        ocr_rows.append(r)

print(f"Loaded {len(ocr_rows)} OCR records from {ocr_csv}")

report_rows = []
chapter_stats = {}

for r in ocr_rows:
    ch = int(r['chapter'])
    sl = int(r['slide'])
    onscreen_raw = r['onscreen_number'].strip()
    l1 = r['line1'].strip()
    l2 = r['line2'].strip()
    l3 = r['line3'].strip()
    
    timing = cuts_rows.get((ch, sl), (0.0, 0.0, 0.0))
    st, en, dur = timing
    
    chapter_stats.setdefault(ch, {'MATCH': 0, 'SHIFTED': 0, 'MERGED': 0, 'SPLIT': 0, 'UNREADABLE': 0, 'TOTAL': 0, 'NON_MATCH': []})
    chapter_stats[ch]['TOTAL'] += 1
    
    if l1 == 'UNREADABLE' or not l1:
        cls = 'UNREADABLE'
        score = 0.0
        match_target = f"Ch{ch}.{sl}"
        report_rows.append({
            'chapter': ch, 'slide': sl, 'onscreen_number': onscreen_raw,
            'data_verse_match': match_target, 'class': cls, 'similarity_score': f"{score:.3f}",
            'start': f"{st:.3f}", 'end': f"{en:.3f}", 'dur': f"{dur:.1f}"
        })
        chapter_stats[ch][cls] += 1
        chapter_stats[ch]['NON_MATCH'].append((sl, onscreen_raw, cls, score, st, en, dur, match_target))
        continue
        
    norm_ocr1 = normalize_deva(l1)
    norm_ocr2 = normalize_deva(l2)
    norm_ocr_all = normalize_deva(f"{l1} {l2} {l3}")
    
    # Candidate data verses
    ch_verses = data_verses[ch]
    # Build line lookups
    v_dict = {int(x['verse_number']): x for x in ch_verses}
    
    # Target candidate
    target_v = v_dict.get(sl)
    target_lines = []
    if target_v:
        raw_t = target_v['text']
        if isinstance(raw_t, list):
            target_lines = [normalize_deva(x) for x in raw_t if normalize_deva(x)]
        else:
            target_lines = [normalize_deva(x) for x in str(raw_t).splitlines() if normalize_deva(x)]
            
    norm_d1 = target_lines[0] if len(target_lines) > 0 else ""
    norm_d2 = target_lines[1] if len(target_lines) > 1 else ""
    norm_d_all = "".join(target_lines)
    
    # 1. Test direct MATCH with data verse sl
    score_direct = sim(norm_ocr1, norm_d1)
    score_all = sim(norm_ocr_all, norm_d_all)
    
    cls = 'MATCH'
    match_target = f"Ch{ch}.{sl}"
    best_score = max(score_direct, score_all)
    
    # If direct score is strong
    if score_direct >= 0.55 or score_all >= 0.60:
        cls = 'MATCH'
        match_target = f"Ch{ch}.{sl}"
        best_score = max(score_direct, score_all)
    else:
        # Search among other verses in the chapter
        best_match_v = None
        best_match_score = 0.0
        best_match_type = None # 'line1', 'line2', 'all'
        
        for cand_num, cand_v in v_dict.items():
            raw_c = cand_v['text']
            c_lines = [normalize_deva(x) for x in (raw_c if isinstance(raw_c, list) else str(raw_c).splitlines()) if normalize_deva(x)]
            cd1 = c_lines[0] if len(c_lines) > 0 else ""
            cd2 = c_lines[1] if len(c_lines) > 1 else ""
            cd_all = "".join(c_lines)
            
            s_l1 = sim(norm_ocr1, cd1)
            s_l2 = sim(norm_ocr1, cd2)
            s_all = sim(norm_ocr_all, cd_all)
            
            if s_l1 > best_match_score:
                best_match_score = s_l1
                best_match_v = cand_num
                best_match_type = 'line1'
            if s_l2 > best_match_score:
                best_match_score = s_l2
                best_match_v = cand_num
                best_match_type = 'line2'
            if s_all > best_match_score:
                best_match_score = s_all
                best_match_v = cand_num
                best_match_type = 'all'
                
        # Check special Ch 1 split/shift pattern (slides 26-36: line 2 of v and line 1 of v+1)
        if ch == 1 and 26 <= sl <= 36:
            cls = 'SHIFTED'
            match_target = f"Ch1.{sl}b + Ch1.{sl+1}a"
            best_score = best_match_score
        elif ch == 1 and sl >= 37:
            # offset by +1
            cls = 'MATCH' if best_match_score >= 0.55 and best_match_v == sl + 1 else 'SHIFTED'
            match_target = f"Ch1.{sl+1}"
            best_score = best_match_score
        elif best_match_score >= 0.55:
            if best_match_v != sl:
                cls = 'SHIFTED'
                match_target = f"Ch{ch}.{best_match_v}"
                best_score = best_match_score
            elif best_match_type == 'line2':
                cls = 'SHIFTED'
                match_target = f"Ch{ch}.{sl} (line 2)"
                best_score = best_match_score
            else:
                cls = 'MATCH'
                match_target = f"Ch{ch}.{best_match_v}"
                best_score = best_match_score
        else:
            cls = 'UNREADABLE'
            match_target = f"Ch{ch}.{sl}"
            best_score = best_match_score
            
    report_rows.append({
        'chapter': ch, 'slide': sl, 'onscreen_number': onscreen_raw,
        'data_verse_match': match_target, 'class': cls, 'similarity_score': f"{best_score:.3f}",
        'start': f"{st:.3f}", 'end': f"{en:.3f}", 'dur': f"{dur:.1f}"
    })
    
    chapter_stats[ch][cls] += 1
    if cls != 'MATCH':
        chapter_stats[ch]['NON_MATCH'].append((sl, onscreen_raw, cls, best_score, st, en, dur, match_target))

# Save _audit/alignment_report.csv
with open(alignment_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['chapter', 'slide', 'onscreen_number', 'data_verse_match', 'class', 'similarity_score', 'start', 'end', 'dur'])
    writer.writeheader()
    writer.writerows(report_rows)

print(f"Saved alignment report to {alignment_csv}")
print("\n=== PER-CHAPTER ALIGNMENT SUMMARY ===")
print("Ch | Total | MATCH | SHIFTED | MERGED | SPLIT | UNREADABLE | Status")
for ch in range(1, 19):
    st = chapter_stats[ch]
    status = "OK" if st['MATCH'] == st['TOTAL'] else ("KNOWN_SHIFT (Ch 1)" if ch == 1 else "ANOMALY")
    print(f"{ch:2d} | {st['TOTAL']:5d} | {st['MATCH']:5d} | {st['SHIFTED']:7d} | {st['MERGED']:6d} | {st['SPLIT']:5d} | {st['UNREADABLE']:10d} | {status}")

print("\n=== NON-MATCH SLIDES DETAIL ===")
for ch in range(1, 19):
    non_matches = chapter_stats[ch]['NON_MATCH']
    if non_matches:
        print(f"\n--- Chapter {ch} ({len(non_matches)} non-match slides) ---")
        for sl, on_num, cls, sc, st, en, dur, tgt in non_matches:
            print(f"  Slide {sl:2d} [onscreen: {on_num:4s}]: {cls:10s} (score {sc:.2f}) -> {tgt} | [{st:8.3f}s to {en:8.3f}s, dur {dur:4.1f}s]")

