from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_env_file(path: Path | None = None) -> Dict[str, str]:
    env_path = path or ROOT_DIR / ".env"
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    backend_url: str
    api_key: str
    mac_ssh_host: str
    mac_project_root: str
    openai_enabled: bool
    openai_api_key: str
    openai_model: str
    config_dir: Path
    data_dir: Path
    logs_dir: Path
    raw_mac_exports_dir: Path


def get_settings() -> Settings:
    env = load_env_file()
    return Settings(
        root_dir=ROOT_DIR,
        backend_url=env.get("VETRI_BACKEND_URL", "http://100.79.123.44:8000").rstrip("/"),
        api_key=env.get("VETRI_API_KEY", ""),
        mac_ssh_host=env.get("MAC_SSH_HOST", "vetri-mac"),
        mac_project_root=env.get("MAC_PROJECT_ROOT", "~/Ashvath-private-cloud"),
        openai_enabled=env_bool(env.get("OPENAI_ENABLED"), default=False),
        openai_api_key=env.get("OPENAI_API_KEY", ""),
        openai_model=env.get("OPENAI_MODEL", "gpt-4o-mini"),
        config_dir=ROOT_DIR / "config",
        data_dir=ROOT_DIR / "data",
        logs_dir=ROOT_DIR / "logs",
        raw_mac_exports_dir=ROOT_DIR / "data" / "raw_imports" / "mac_exports",
    )
