import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("backend/data/multimodal/source/vyom_clips.json", encoding="utf-8") as f:
    clips = json.load(f)

by_id = {c["clip_id"]: c for c in clips}
for cid in ["bg_01_26", "bg_01_27", "bg_01_28", "bg_01_36", "bg_01_37", "bg_01_46", "bg_04_29", "bg_04_30", "bg_04_31"]:
    c = by_id[cid]
    print(f"{cid}: data_verses={c['data_verses']}, partial={c['partial']}, speaker={c['speaker']}")

