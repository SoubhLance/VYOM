import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path("backend/data/multimodal/source")
V5_PATH = ROOT / "vyom_clips_v5.json"
OUT_PATH = ROOT / "verse_clips.json"

with open(V5_PATH, "r", encoding="utf-8") as f:
    clips = json.load(f)

# Sort clips in slide order (by chapter, slide)
clips.sort(key=lambda c: (c["chapter"], c["slide"]))

# Collect all 701 data verses from backend/data/gita
all_verses = []
for ch in range(1, 19):
    with open(f"backend/data/gita/{ch}/verses.json", "r", encoding="utf-8") as f:
        v_data = json.load(f)
    for row in v_data:
        all_verses.append((ch, row["verse_number"]))

assert len(all_verses) == 701, f"Expected 701 verses, got {len(all_verses)}"

# For each verse, find all clips that touch it in slide order
verse_clips_dict = {}
for ch, v in all_verses:
    key = f"{ch}.{v}"
    touching_clips = []
    for c in clips:
        if c["chapter"] == ch and v in c["data_verses"]:
            touching_clips.append({
                "clip_id": c["clip_id"],
                "audio_path": c["audio_path"],
                "partial": c["partial"],
                "spoken_lines": c["spoken_lines"],
            })
    verse_clips_dict[key] = {
        "chapter": ch,
        "verse": v,
        "clips": touching_clips,
    }

# Save S/verse_clips.json
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(verse_clips_dict, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(verse_clips_dict)} entries to {OUT_PATH}")

# Checks:
# 1. Every one of the 701 verses has at least one clip
has_at_least_one = all(len(entry["clips"]) >= 1 for entry in verse_clips_dict.values())
print(f"Check 1: Every one of the 701 verses has >= 1 clip: {has_at_least_one}")
assert has_at_least_one

# 2. Every one of the 700 clips appears at least once
all_seen_clip_ids = set()
for entry in verse_clips_dict.values():
    for c in entry["clips"]:
        all_seen_clip_ids.add(c["clip_id"])
all_v5_clip_ids = {c["clip_id"] for c in clips}
print(f"Check 2: Every one of the 700 clips appears at least once: {all_seen_clip_ids == all_v5_clip_ids} ({len(all_seen_clip_ids)}/700)")
assert all_seen_clip_ids == all_v5_clip_ids

# 3. Print count and first 10 verses that have >= 2 clips
ge_2_verses = [key for key, entry in verse_clips_dict.items() if len(entry["clips"]) >= 2]
print(f"Check 3: Count of verses with >= 2 clips: {len(ge_2_verses)}")
print("First 10 verses with >= 2 clips:")
for key in ge_2_verses[:10]:
    clip_ids = [c["clip_id"] for c in verse_clips_dict[key]["clips"]]
    print(f"  {key}: {len(verse_clips_dict[key]['clips'])} clips -> {clip_ids}")

# 4. Print full entries for 1.27, 4.30, 6.23 and 2.47
print("\n" + "="*50)
for sample_key in ["1.27", "4.30", "6.23", "2.47"]:
    print(f"\n--- Full entry for {sample_key} ---")
    print(json.dumps(verse_clips_dict[sample_key], ensure_ascii=False, indent=2))

