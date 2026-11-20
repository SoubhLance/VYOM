import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("backend/data/multimodal/source/vyom_clips_v5.json", "r", encoding="utf-8") as f:
    clips = json.load(f)

print("First clip audio_path:", clips[0]["audio_path"])
print("Types:", {k: type(clips[0][k]).__name__ for k in ["clip_id", "audio_path", "partial", "spoken_lines"]})

