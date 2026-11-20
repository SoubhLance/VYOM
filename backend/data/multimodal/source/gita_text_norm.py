import json
import pathlib
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')


def search_norm(s):
  """Normalizes Devanagari Sanskrit text for flexible search and indexing.

  Steps:
  1. NFC Unicode normalization.
  2. Remove stray U+093C (Devanagari sign nukta).
  3. Remove Zero-Width Joiner (ZWJ U+200D) and Zero-Width Non-Joiner (ZWNJ
  U+200C).
  4. Remove avagraha (ऽ U+093D).
  5. Replace erroneous 'श्रृ' with canonical 'शृ'.
  6. Standardize class-nasals + halant before their own class consonants
  (ङ्, ञ्, ण्, न्, म्) to anusvara (ं U+0902).
  7. Collapse all whitespace runs to single spaces and strip outer padding.
  """
  if isinstance(s, list):
    t = ' '.join(s)
  else:
    t = str(s)

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

  # 6. replace class-nasal+halant variants with ं
  t = re.sub(r'ङ्([कखगघङ])', r'ं\1', t)
  t = re.sub(r'ञ्([चछजझञ])', r'ं\1', t)
  t = re.sub(r'ण्([टठडढण])', r'ं\1', t)
  t = re.sub(r'न्([तथदधन])', r'ं\1', t)
  t = re.sub(r'म्([पफबभम])', r'ं\1', t)

  # 7. collapse whitespace
  t = re.sub(r'\s+', ' ', t).strip()

  return t


if __name__ == '__main__':
  S = pathlib.Path(__file__).parent
  v4_path = S / 'vyom_clips_v4.json'
  if not v4_path.exists():
    v4_path = pathlib.Path('backend/data/multimodal/source/vyom_clips_v4.json')

  with open(v4_path, encoding='utf-8') as f:
    v4_clips = json.load(f)

  passed = 0
  for clip in v4_clips:
    norm_val = search_norm(clip['spoken_lines'])
    expected = clip['search_text']
    assert norm_val == expected, (
        f"Mismatch on {clip['clip_id']}:\nGot:      {norm_val}\nExpected:"
        f' {expected}'
    )
    passed += 1

  print(
      f'Self-test passed: search_norm matched search_text across all {passed}'
      ' v4 clips.'
  )

