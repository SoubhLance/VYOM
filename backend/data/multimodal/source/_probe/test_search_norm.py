import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')


def make_search_text(text):
  # 1. NFC normalization
  t = unicodedata.normalize('NFC', text)

  # 2. remove U+093C (nukta)
  t = t.replace('\u093c', '')

  # 3. remove ZWJ (\u200d) and ZWNJ (\u200c)
  t = t.replace('\u200d', '').replace('\u200c', '')

  # 4. remove avagraha (ऽ, \u093d)
  t = t.replace('ऽ', '').replace('\u093d', '')

  # 5. replace श्रृ with शृ (\u0936\u094d\u0930\u0943 -> \u0936\u0943)
  t = t.replace('श्रृ', 'शृ')

  # 6. replace class-nasal + halant variants with anusvara (ं, \u0902)
  # Ka-varga: ङ् + [कखगघङ] -> ं + consonant
  t = re.sub(r'ङ्([कखगघङ])', r'ं\1', t)
  # Cha-varga: ञ् + [चछजझञ] -> ं + consonant
  t = re.sub(r'ञ्([चछजझञ])', r'ं\1', t)
  # Retroflex Ta-varga: ण् + [टठडढण] -> ं + consonant
  t = re.sub(r'ण्([टठडढण])', r'ं\1', t)
  # Dental Ta-varga: न् + [तथदधन] -> ं + consonant
  t = re.sub(r'न्([तथदधन])', r'ं\1', t)
  # Pa-varga: म् + [पफबभम] -> ं + consonant
  t = re.sub(r'म्([पफबभम])', r'ं\1', t)

  # 7. collapse whitespace
  t = re.sub(r'\s+', ' ', t).strip()

  return t


# Test examples
examples = [
    'पश्यन् श्रृणवन्स्पृशञ्जिघ्रन्नश्नन्गच्छन्स्वपन् श्वसन्',
    'सङ्कल्पप्रभवान्कामांस्त्यक्त्वा सर्वानशेषतः',
    'सञ्जय उवाच',
    'संजय उवाच',
    'किञ्चित्करोमीति',
    'किंचित्करोमीति',
    'द्रव्ययज्ञास्तपोयज्ञा योगयज्ञास्तथाऽपरे',
    'मातुलाः श्वशुराः पौत्राः श्यालाः सम्बन्धिनस्तथा',
]

for ex in examples:
  print(f'{repr(ex)} ->\n  {repr(make_search_text(ex))}\n')

