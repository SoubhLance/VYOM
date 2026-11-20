import json
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

with open("backend/data/gita/18/verses.json", "r", encoding="utf-8") as f:
    data = json.load(f)

v = [x for x in data if x.get("verse_number") == 6][0]
raw_text = v["text"]

print(f"Raw text of 18.6:\n{raw_text}\n")

# Split on danda '।' to get line 1 and line 2
parts = raw_text.split("।")
print(f"Line 1: {parts[0].strip()}।")
line2 = parts[1].strip()
print(f"Line 2: {line2}\n")

# Search for the word in line 2
words = line2.split()
matched_word = None
for w in words:
    if "निश्" in w or "चित" in w or "श्चि" in w:
        matched_word = w
        break

print(f"Word in raw text line 2: {matched_word!r}")
print("Codepoints in matched word:")
for i, ch in enumerate(matched_word):
    cp = f"U+{ord(ch):04X}"
    name = unicodedata.name(ch, "UNKNOWN")
    print(f"  {ch!r} -> {cp} ({name})")

user_target = "निश्िचतं"
print(f"\nUser query word: {user_target!r}")
print("Codepoints in user query word:")
for i, ch in enumerate(user_target):
    cp = f"U+{ord(ch):04X}"
    name = unicodedata.name(ch, "UNKNOWN")
    print(f"  {ch!r} -> {cp} ({name})")

