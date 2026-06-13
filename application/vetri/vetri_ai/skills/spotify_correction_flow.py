from __future__ import annotations

from pathlib import Path
from typing import Any

from vetri_ai.memory.spotify_memory import backup_spotify_memory, load_spotify_memory, save_spotify_memory


def propose_correction(spoken: str, intended: str) -> dict[str, Any]:
    return {
        "ok": True,
        "requires_confirmation": True,
        "message": f"Correction staged: map '{spoken}' to '{intended}'. Say confirm before saving.",
        "spoken": spoken,
        "intended": intended
    }


def confirm_correction(spoken: str, intended: str, root: Path | None = None) -> dict[str, Any]:
    memory = load_spotify_memory(root=root)
    backup = backup_spotify_memory(root=root)
    corrections = memory.setdefault("corrections", {})
    corrections[spoken] = intended
    save_spotify_memory(memory, root=root)
    return {"ok": True, "backup": str(backup), "message": "Spotify correction saved after confirmation."}
