from __future__ import annotations

from pathlib import Path


def ensure_file(path: Path, default_text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(default_text, encoding="utf-8")


def ensure_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
