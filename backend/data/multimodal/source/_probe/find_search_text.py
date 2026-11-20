import pathlib
import re

for p in pathlib.Path('backend').rglob('*.py'):
  try:
    content = p.read_text(encoding='utf-8')
    if 'search_text' in content:
      print(f'Found search_text in: {p}')
    if 'normalize' in content.lower() and 'nasal' in content.lower():
      print(f'Found nasal normalization in: {p}')
  except Exception:
    pass

