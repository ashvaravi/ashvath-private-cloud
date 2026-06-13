from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def to_pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def backup_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.name}.{stamp}.bak")


def broken_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.name}.broken.{stamp}")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        path.rename(broken_path(path))
        return default


def load_json_file(path: Path) -> Any:
    loaded = load_json(path, default=None)
    if loaded is None:
        raise FileNotFoundError(f"JSON file missing or malformed: {path}")
    return loaded


def save_json(path: Path, data: Any, backup: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        shutil.copy2(path, backup_path(path))
    path.write_text(to_pretty_json(data) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
        except json.JSONDecodeError:
            continue
    return rows[-limit:] if limit else rows
