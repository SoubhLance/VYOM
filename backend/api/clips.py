"""Multimodal clip retrieval and audio serving for VYOM API."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

logger = logging.getLogger("vyom.clips")

# Base directory paths
# Path(__file__).resolve().parents[1] is backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_VERSE_CLIPS = BACKEND_ROOT / "data" / "multimodal" / "verse_clips.json"
DEFAULT_AUDIO_DIR = BACKEND_ROOT / "data" / "multimodal" / "source" / "assets" / "audio"

_VERSE_CLIPS: dict[str, Any] | None = None


def get_audio_dir() -> Path:
    """Resolve audio directory path from env or default."""
    path_str = os.environ.get("VYOM_AUDIO_DIR")
    if path_str:
        return Path(path_str).resolve()
    return DEFAULT_AUDIO_DIR.resolve()


def load_verse_clips() -> dict[str, Any]:
    """Reads verse_clips.json once and caches the result in-memory.
    Path is read from env VYOM_VERSE_CLIPS, defaulting to backend/data/multimodal/verse_clips.json.
    """
    global _VERSE_CLIPS
    if _VERSE_CLIPS is not None:
        return _VERSE_CLIPS

    env_path = os.environ.get("VYOM_VERSE_CLIPS")
    target_path = Path(env_path).resolve() if env_path else DEFAULT_VERSE_CLIPS.resolve()

    if not target_path.exists():
        logger.warning("verse_clips.json not found at %s", target_path)
        _VERSE_CLIPS = {}
        return _VERSE_CLIPS

    with open(target_path, "r", encoding="utf-8") as f:
        _VERSE_CLIPS = json.load(f)

    logger.info("Loaded %d verse clip mappings from %s", len(_VERSE_CLIPS), target_path)
    return _VERSE_CLIPS


def clips_for(verse_id: str) -> list[dict[str, Any]]:
    """Retrieve audio clips for a given verse_id (e.g. '2.47', '1.27').
    Returns a list of dicts with keys:
        - clip_id (str)
        - audio_url (str, e.g. '/audio/verses/bg_02_47.mp3')
        - partial (bool)
        - spoken_lines (list[str])
    """
    store = load_verse_clips()
    entry = store.get(str(verse_id))
    if not entry or "clips" not in entry:
        return []

    results = []
    for c in entry["clips"]:
        raw_path = c.get("audio_path", "")
        # Remove leading "audio/" or "audio\\" if present
        clean_path = raw_path
        if clean_path.startswith("audio/") or clean_path.startswith("audio\\"):
            clean_path = clean_path[6:]
        clean_path = clean_path.lstrip("/\\").replace("\\", "/")
        audio_url = f"/audio/{clean_path}"

        results.append({
            "clip_id": c.get("clip_id"),
            "audio_url": audio_url,
            "partial": c.get("partial", False),
            "spoken_lines": c.get("spoken_lines", []),
        })
    return results


def get_audio_static() -> StaticFiles:
    """Create a StaticFiles application serving the audio directory read-only."""
    audio_dir = get_audio_dir()
    return StaticFiles(directory=str(audio_dir), check_dir=False)


# StaticFiles mount instance
audio_static = get_audio_static()


def mount_audio(app: FastAPI, prefix: str = "/audio") -> None:
    """Mount StaticFiles audio serving onto a FastAPI instance with path traversal protection."""
    app.mount(prefix, get_audio_static(), name="audio")


# Optional APIRouter implementation for /audio with traversal protection
audio_router = APIRouter()


@audio_router.get("/audio/{file_path:path}")
async def serve_audio_file(file_path: str):
    """Serve audio file securely with strict path traversal prevention."""
    base_dir = get_audio_dir()
    target = (base_dir / file_path).resolve()
    # Path traversal check
    try:
        target.relative_to(base_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not target.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(target, media_type="audio/mpeg")

