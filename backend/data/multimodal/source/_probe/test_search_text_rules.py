import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')


def make_search_text(lines):
  if isinstance(lines, list):
    t = ' '.join(lines)
  else:
    t = str(lines)

  # 1. NFC normalization
  t = unicodedata.normalize('NFC', t)

  # 2. remove U+093C (nukta)
  t = t.replace('\u093c', '')

  # 3. remove ZWJ (\u200d) and ZWNJ (\u200c)
  t = t.replace('\u200d', '').replace('\u200c', '')

  # 4. remove avagraha (ऽ, \u093d)
  t = t.replace('ऽ', '').replace('\u093d', '')

  # 5. replace श्रृ with शृ (\u0936\u094d\u0930\u0943 -> \u0936\u0943)
  t = t.replace('श्रृ', 'शृ')

  # 6. replace anusvara/class-nasal+halant variants:
  # ङ् followed by [कखगघङ] -> ं
  t = re.sub(r'ङ्([कखगघङ])', r'ं\1', t)
  # ञ् followed by [चछजझञ] -> ं
  t = re.sub(r'ञ्([चछजझञ])', r'ं\1', t)
  # ण् followed by [टठडढण] -> ं
  t = re.sub(r'ण्([टठडढण])', r'ं\1', t)
  # न् followed by [तथदधन] -> ं
  t = re.sub(r'न्([तथदधन])', r'ं\1', t)
  # म् followed by [पफबभम] -> ं
  t = re.sub(r'म्([पफबभम])', r'ं\1', t)

  # 7. collapse whitespace
  t = re.sub(r'\s+', ' ', t).strip()

  return t


# Let's test on several specific verse lines from the Gita:
test_cases = [
    # Ka-varga
    ('सङ्गदोषः', 'संगदोषः'),
    ('शङ्खान्', 'शंखान्'),
    # Cha-varga
    ('किञ्चित्', 'किंचित्'),
    ('सञ्जय', 'संजय'),
    # Ta-varga (retroflex)
    ('कुण्ठित', 'कुंठित'),
    # Ta-varga (dental)
    ('शान्ति', 'शांति'),
    ('हन्तुम्', 'हंतुम्'),
    ('बन्धु', 'बंधु'),
    # Pa-varga
    ('सम्बन्धिनः', 'संबंधिनः'),
    ('सम्पर्क', 'संपर्क'),
    # Avagraha
    ('सोऽहम्', 'सोहम्'),
    ('मेऽच्युत', 'मेच्युत'),
    # Shring / Shringara
    ('श्रृण्वन्', 'शृण्वन्'),
    ('श्रृणु', 'शृणु'),
    # Nukta
    ('पितृ़न्', 'पितृन्'),
]

for inp, expected in test_cases:
  out = make_search_text(inp)
  assert (
      out == expected
  ), f"Failed for {inp}: expected {expected}, got {out} (repr: {repr(out)})"
  print(f'OK: {inp} -> {out}')

