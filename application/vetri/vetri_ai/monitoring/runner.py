from __future__ import annotations

from pathlib import Path

from vetri_ai.monitoring.rules import evaluate_rules
from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import append_jsonl, save_json
from vetri_ai.utils.time_utils import now_iso


def run_monitoring(root: Path = ROOT_DIR) -> dict[str, object]:
    findings = [finding.to_dict() for finding in evaluate_rules()]
    warning_count = len([item for item in findings if item["status"] != "ok"])
    report = {
        "timestamp": now_iso(),
        "ok": warning_count == 0,
        "warning_count": warning_count,
        "findings": findings,
        "summary": f"Read-only monitoring completed with {warning_count} warning(s)."
    }
    out_dir = root / "logs" / "monitoring"
    save_json(out_dir / "latest_monitoring_report.json", report)
    append_jsonl(out_dir / "monitoring_history.jsonl", report)
    return report


def format_monitoring_report(report: dict[str, object]) -> str:
    lines = [str(report.get("summary", "Read-only monitoring completed."))]
    for item in report.get("findings", []):
        if isinstance(item, dict):
            lines.append(f"- {item.get('rule')}: {item.get('status')} - {item.get('message')}")
    return "\n".join(lines)
