import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Speaker patterns to check/remove
# (श्रीभगवानुवाच, अर्जुन उवाच, सञ्जय उवाच, धृतराष्ट्र उवाच)
speakers = [
    'श्री भगवानुवाच', # in data it has space
    'श्रीभगवानुवाच',
    'अर्जुन उवाच',
    'सञ्जय उवाच',
    'धृतराष्ट्र उवाच'
]

def normalize_verse(t, ch, v_num):
    # 1. strip U+093C
    t = t.replace('\u093c', '')
    
    # Check speaker
    found_speaker = None
    for sp in speakers:
        if sp in t:
            if 'भगवानुवाच' in sp:
                found_speaker = 'श्रीभगवानुवाच'
            else:
                found_speaker = sp
            # remove speaker label
            t = t.replace(sp, '')
            break
            
    # 2. remove trailing ।।C.V।। marker
    t = re.sub(r'[।|॥]+\s*\d+\.\d+\s*[।|॥]+\s*$', '', t)
    
    # 3. split on । (drop empty strings)
    # Let's test s.strip() vs raw s
    raw_parts = t.split('।')
    lines = [p.strip() for p in raw_parts if p.strip()]
    
    return found_speaker, lines

not_two = []
total_verses = 0

for ch in range(1, 19):
    with open(f"backend/data/gita/{ch}/verses.json", encoding="utf-8") as f:
        verses = json.load(f)
    for v in verses:
        total_verses += 1
        sp, lines = normalize_verse(v['text'], ch, v['verse_number'])
        if len(lines) != 2:
            not_two.append((ch, v['verse_number'], len(lines), lines))

print(f"Total verses processed: {total_verses}")
print(f"Verses not splitting into exactly 2 lines: {len(not_two)}")
print("First 10 examples:")
for ch, vn, l_len, lns in not_two[:10]:
    print(f"  Ch {ch}.{vn} -> {l_len} lines: {lns}")
