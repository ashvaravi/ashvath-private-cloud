from __future__ import annotations

from pathlib import Path
from typing import Any

from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import load_json


def spotify_memory_path(root: Path = ROOT_DIR) -> Path:
    return root / "voice" / "memory" / "spotify_memory.json"


def summarize_spotify_memory(root: Path = ROOT_DIR) -> dict[str, Any]:
    path = spotify_memory_path(root)
    if not path.exists():
        return {"ok": True, "status": "missing", "message": "No Spotify memory file exists yet.", "path": str(path)}
    data = load_json(path, default={})
    if not isinstance(data, dict):
        data = {}
    return {
        "ok": True,
        "status": "read",
        "path": str(path),
        "top_level_keys": sorted(data.keys()),
        "learned_tracks_count": len(data.get("learned_tracks", data.get("tracks", {})) or {}),
        "aliases_count": len(data.get("aliases", {}) or {}),
        "failed_searches_count": len(data.get("failed_searches", []) or []),
        "stt_corrections_count": len(data.get("stt_corrections", {}) or {}),
        "regional_notes": [
            "Regional song names may be English transliteration or native script.",
            "Tamil Unicode must not be stripped.",
            "Artist-heavy search can overpower title intent.",
            "Use aliases, title guards, and explicit correction flow before learning mappings."
        ]
    }


def explain_regional_song_issue() -> str:
    return (
        "Tamil/regional Spotify search can fail because STT may output transliteration, Tamil Unicode, or wrong phonetics; "
        "Spotify ranking can over-weight artist names; and without title guards Vetri may learn a plausible but wrong match. "
        "The fix is Unicode-safe normalization, aliases, title guards, explicit memory correction, and better STT for music commands later."
    )
