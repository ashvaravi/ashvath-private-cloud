from __future__ import annotations

from pathlib import Path

from vetri_ai.safety.sanitizer import sanitize_value
from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import append_jsonl, load_json, read_jsonl


def extract_mac_export_events(root: Path = ROOT_DIR) -> dict[str, object]:
    source = root / "data" / "raw_imports" / "mac_exports"
    out = root / "data" / "cleaned_events"
    counts = {"system": 0, "backup": 0, "service": 0, "homeassistant": 0}
    mapping = {
        "latest_status_snapshot.json": ("system_events.jsonl", "system"),
        "latest_backup_summary.json": ("backup_events.jsonl", "backup"),
        "latest_service_summary.json": ("service_events.jsonl", "service"),
        "latest_homeassistant_summary.json": ("homeassistant_events.jsonl", "homeassistant")
    }
    for filename, (target, key) in mapping.items():
        data = load_json(source / filename, default=None)
        if data is not None:
            append_jsonl(out / target, {"source": filename, "event": sanitize_value(data)})
            counts[key] += 1
    for event in read_jsonl(source / "sanitized_events.jsonl"):
        append_jsonl(out / "system_events.jsonl", {"source": "sanitized_events.jsonl", "event": sanitize_value(event)})
        counts["system"] += 1
    return {"ok": True, "counts": counts}
