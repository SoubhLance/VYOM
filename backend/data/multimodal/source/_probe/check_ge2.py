import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("backend/data/multimodal/source/vyom_clips_v5.json", "r", encoding="utf-8") as f:
    clips = json.load(f)

# Sort clips in slide order
clips.sort(key=lambda c: (c["chapter"], c["slide"]))

verses_with_clips = {}
for c in clips:
    ch = c["chapter"]
    for v in c["data_verses"]:
        verses_with_clips.setdefault((ch, v), []).append(c)

print(f"Total verses with >= 2 clips: {sum(1 for c_list in verses_with_clips.values() if len(c_list) >= 2)}")
print("List of verses with >= 2 clips:")
for (ch, v), c_list in sorted(verses_with_clips.items()):
    if len(c_list) >= 2:
        clip_ids = [c["clip_id"] for c in c_list]
        print(f"  {ch}.{v}: {len(c_list)} clips -> {clip_ids}")

