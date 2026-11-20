import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("backend/data/multimodal/source/vyom_clips_v5.json", "r", encoding="utf-8") as f:
    clips = json.load(f)

for c in clips:
    if c["chapter"] == 1 and c["slide"] in [20, 21, 22, 26, 27, 28]:
        print(f"Slide {c['slide']}: clip_id={c['clip_id']}, data_verses={c['data_verses']}, partial={c['partial']}, lines={len(c['spoken_lines'])}")

