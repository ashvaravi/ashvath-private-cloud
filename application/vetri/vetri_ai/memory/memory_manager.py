from __future__ import annotations

from pathlib import Path
from typing import Any

from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import append_jsonl, load_json, read_jsonl, save_json
from vetri_ai.utils.time_utils import now_iso, today_iso


class MemoryManager:
    def __init__(self, root: Path = ROOT_DIR) -> None:
        self.root = root
        self.data = root / "data"
        self.personal = self.data / "personal_memory"
        self.project = self.data / "project_memory"
        self.incidents = self.data / "incident_memory"
        self.daily = self.data / "daily_summaries"

    def ensure_memory_files(self) -> None:
        for path in [
            self.personal / "preferences.json",
            self.personal / "aliases.json",
            self.personal / "routines.json",
            self.project / "endpoint_inventory.json",
            self.incidents / "incident_index.json",
        ]:
            if not path.exists():
                save_json(path, {}, backup=False)
        for path in [
            self.personal / "user_memory.jsonl",
            self.project / "architecture_decisions.jsonl",
            self.project / "completed_phases.jsonl",
            self.project / "recovery_notes.jsonl",
            self.incidents / "incidents.jsonl",
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)

    def append_event(self, event: dict[str, Any]) -> None:
        event.setdefault("timestamp", now_iso())
        append_jsonl(self.project / "architecture_decisions.jsonl", event)

    def get_recent_events(self, limit: int = 10) -> list[dict[str, Any]]:
        return read_jsonl(self.project / "completed_phases.jsonl", limit=limit)

    def save_project_event(self, summary: str, phase: str = "windows_brain") -> None:
        append_jsonl(self.project / "completed_phases.jsonl", {"timestamp": now_iso(), "phase": phase, "summary": summary})

    def save_incident(self, incident: dict[str, Any]) -> None:
        incident.setdefault("timestamp", now_iso())
        append_jsonl(self.incidents / "incidents.jsonl", incident)

    def update_user_preference(self, text: str) -> dict[str, Any]:
        item = {"timestamp": now_iso(), "type": "preference", "summary": text}
        append_jsonl(self.personal / "user_memory.jsonl", item)
        return item

    def save_daily_summary(self, summary: dict[str, Any]) -> None:
        summary.setdefault("date", today_iso())
        year_dir = self.daily / summary["date"][:4]
        save_json(year_dir / f"{summary['date']}.json", summary)
        save_json(self.daily / "latest_daily_summary.json", summary)

    def load_memory_summary(self) -> dict[str, Any]:
        return {
            "preferences": load_json(self.personal / "preferences.json", {}),
            "recent_project_events": self.get_recent_events(15),
            "recent_personal_memory": read_jsonl(self.personal / "user_memory.jsonl", limit=10),
            "incidents": read_jsonl(self.incidents / "incidents.jsonl", limit=10),
            "latest_daily_summary": load_json(self.daily / "latest_daily_summary.json", {})
        }

    def forget_last_memory(self) -> dict[str, Any]:
        path = self.personal / "user_memory.jsonl"
        rows = read_jsonl(path)
        if not rows:
            return {"ok": False, "message": "No personal memory exists to forget."}
        removed = rows.pop()
        path.write_text("".join(__import__("json").dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        return {"ok": True, "removed": removed}

    def review_memory(self) -> dict[str, Any]:
        return self.load_memory_summary()

    def compact_memory(self) -> dict[str, Any]:
        return {"ok": True, "message": "Memory compaction scaffold present. No destructive compaction performed."}

    def cleanup_by_retention_policy(self) -> dict[str, Any]:
        return {"ok": True, "message": "Retention cleanup scaffold present. No files deleted in foundation smoke path."}
