from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import load_json, save_json
from vetri_ai.utils.time_utils import now_iso


def source_path(root: Path | None = None) -> Path:
    base = root or ROOT_DIR
    return base / "voice" / "memory" / "spotify_memory.json"


def local_path(root: Path | None = None) -> Path:
    base = root or ROOT_DIR
    return base / "data" / "personal_memory" / "spotify_memory_v4.json"


def load_spotify_memory(root: Path | None = None) -> dict[str, Any]:
    path = source_path(root)
    data = load_json(path, default={}) if path.exists() else load_json(local_path(root), default={})
    return data if isinstance(data, dict) else {}


def backup_spotify_memory(root: Path | None = None) -> Path:
    base = root or ROOT_DIR
    src = source_path(base)
    backup_dir = base / "data" / "personal_memory" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_iso().replace(":", "").replace("-", "")
    backup = backup_dir / f"spotify_memory_{stamp}.json"
    if src.exists():
        shutil.copy2(src, backup)
    else:
        save_json(backup, {}, backup=False)
    return backup


def save_spotify_memory(memory: dict[str, Any], root: Path | None = None) -> None:
    save_json(local_path(root), memory)
