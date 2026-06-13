from __future__ import annotations

from pathlib import Path
from typing import Any

from vetri_ai.safety.sanitizer import sanitize_value
from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import append_jsonl
from vetri_ai.utils.time_utils import now_iso


class AuditLogger:
    def __init__(self, audit_log_path: Path | None = None, error_log_path: Path | None = None) -> None:
        self.audit_log_path = audit_log_path or ROOT_DIR / "logs" / "command_audit.jsonl"
        self.error_log_path = error_log_path or ROOT_DIR / "logs" / "errors.jsonl"

    def log_command(self, record: dict[str, Any]) -> None:
        record = sanitize_value(record)
        record.setdefault("timestamp", now_iso())
        append_jsonl(self.audit_log_path, record)

    def log_error(self, record: dict[str, Any]) -> None:
        record = sanitize_value(record)
        record.setdefault("timestamp", now_iso())
        append_jsonl(self.error_log_path, record)
