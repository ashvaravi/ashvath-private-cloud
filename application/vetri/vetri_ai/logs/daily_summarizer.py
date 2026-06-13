from __future__ import annotations

from pathlib import Path

from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import load_json, read_jsonl, save_json
from vetri_ai.utils.time_utils import today_iso


def build_daily_summary(root: Path = ROOT_DIR) -> dict[str, object]:
    date = today_iso()
    project_events = read_jsonl(root / "data" / "project_memory" / "completed_phases.jsonl", limit=20)
    incidents = read_jsonl(root / "data" / "incident_memory" / "incidents.jsonl", limit=5)
    manifest = load_json(root / "data" / "raw_imports" / "mac_exports" / "export_manifest.json", default={})
    summary = {
        "date": date,
        "milestones": [str(item.get("summary", item)) for item in project_events[-8:]],
        "failures": [str(item.get("title", item.get("summary", item))) for item in incidents[-3:]],
        "fixes": [],
        "decisions": ["Preserve stable terminal voice layer; AI brain remains deterministic and safety-routed."],
        "next_recommended_steps": ["Run Mac sync when reachable.", "Strengthen Spotify regional NLP correction/title-guard flow.", "Expand read-only diagnosis coverage from synced exports."],
        "mac_export_manifest_present": bool(manifest),
        "safe_for_ai": True
    }
    target = root / "data" / "daily_summaries" / date[:4] / f"{date}.json"
    save_json(target, summary)
    save_json(root / "data" / "daily_summaries" / "latest_daily_summary.json", summary)
    return summary
