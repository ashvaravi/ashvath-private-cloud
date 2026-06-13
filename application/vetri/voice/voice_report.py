from __future__ import annotations

import argparse
import html
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


VOICE_DIR = Path(__file__).resolve().parent
LOG_PATH = VOICE_DIR / "logs" / "voice_sessions.jsonl"
REPORT_DIR = VOICE_DIR / "reports"
REPORT_PATH = REPORT_DIR / "voice_report.html"


def load_events() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []

    events: list[dict[str, Any]] = []

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            clean = line.strip()

            if not clean:
                continue

            try:
                event = json.loads(clean)

                if isinstance(event, dict):
                    events.append(event)

            except json.JSONDecodeError:
                continue

    return events


def safe_text(value: Any) -> str:
    if value is None:
        return ""

    return html.escape(str(value))


def format_timestamp(value: Any) -> str:
    if not value:
        return ""

    text = str(value)

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return text


def classify_status(event: dict[str, Any]) -> str:
    if event.get("blocked"):
        return "Blocked"

    if event.get("error"):
        return "Error"

    return_code = event.get("return_code")

    if return_code is None:
        command_type = event.get("command_type") or event.get("mode")

        if command_type == "local_voice":
            return "Local"

        if event.get("matched_command"):
            return "No Return Code"

        return "No Match"

    try:
        if int(return_code) == 0:
            return "Success"

        return "Failed"
    except Exception:
        return "Unknown"


def status_class(status: str) -> str:
    normalized = status.lower()

    if normalized == "success":
        return "success"

    if normalized in {"blocked", "failed", "error"}:
        return "danger"

    if normalized in {"local", "no return code"}:
        return "neutral"

    return "warning"


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)

    status_counts = Counter(classify_status(event) for event in events)
    command_counts = Counter(
        event.get("matched_command") or "No matched command"
        for event in events
    )
    risk_counts = Counter(
        event.get("policy_risk") or "none"
        for event in events
    )
    version_counts = Counter(
        event.get("version") or "unknown"
        for event in events
    )

    durations = []

    for event in events:
        duration = event.get("duration_seconds")

        try:
            durations.append(float(duration))
        except Exception:
            pass

    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0

    return {
        "total": total,
        "status_counts": status_counts,
        "command_counts": command_counts,
        "risk_counts": risk_counts,
        "version_counts": version_counts,
        "avg_duration": avg_duration,
    }


def render_counter_rows(counter: Counter, empty_label: str) -> str:
    if not counter:
        return f"<tr><td colspan='2'>{safe_text(empty_label)}</td></tr>"

    rows = []

    for key, count in counter.most_common():
        rows.append(
            "<tr>"
            f"<td>{safe_text(key)}</td>"
            f"<td>{safe_text(count)}</td>"
            "</tr>"
        )

    return "\n".join(rows)


def render_recent_rows(events: list[dict[str, Any]], limit: int) -> str:
    if not events:
        return "<tr><td colspan='9'>No voice sessions logged yet.</td></tr>"

    rows = []

    for event in list(reversed(events[-limit:])):
        status = classify_status(event)
        css = status_class(status)

        rows.append(
            "<tr>"
            f"<td>{safe_text(format_timestamp(event.get('timestamp_utc')))}</td>"
            f"<td><span class='badge {css}'>{safe_text(status)}</span></td>"
            f"<td>{safe_text(event.get('version'))}</td>"
            f"<td>{safe_text(event.get('mode') or event.get('command_type'))}</td>"
            f"<td>{safe_text(event.get('transcript'))}</td>"
            f"<td>{safe_text(event.get('corrected_transcript'))}</td>"
            f"<td>{safe_text(event.get('matched_command'))}</td>"
            f"<td>{safe_text(event.get('policy_risk'))}</td>"
            f"<td>{safe_text(event.get('spoken_summary'))}</td>"
            "</tr>"
        )

    return "\n".join(rows)


def build_html(events: list[dict[str, Any]], limit: int) -> str:
    summary = summarize_events(events)

    total = summary["total"]
    status_counts: Counter = summary["status_counts"]
    command_counts: Counter = summary["command_counts"]
    risk_counts: Counter = summary["risk_counts"]
    version_counts: Counter = summary["version_counts"]
    avg_duration = summary["avg_duration"]

    success_count = status_counts.get("Success", 0)
    blocked_count = status_counts.get("Blocked", 0)
    error_count = status_counts.get("Error", 0) + status_counts.get("Failed", 0)

    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Vetri Voice Report</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: #121a2f;
      --panel-2: #18223d;
      --text: #ecf2ff;
      --muted: #9fb0d0;
      --border: rgba(255,255,255,0.12);
      --accent: #ff8a00;
      --success: #16a34a;
      --danger: #dc2626;
      --warning: #d97706;
      --neutral: #2563eb;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: radial-gradient(circle at top left, #1d2b53 0, var(--bg) 42%);
      color: var(--text);
    }}

    .page {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px;
    }}

    .hero {{
      background: linear-gradient(135deg, rgba(255,138,0,0.16), rgba(37,99,235,0.14));
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 28px;
      margin-bottom: 24px;
      box-shadow: 0 18px 50px rgba(0,0,0,0.24);
    }}

    h1 {{
      margin: 0 0 8px 0;
      font-size: 34px;
      letter-spacing: -0.6px;
    }}

    .subtitle {{
      color: var(--muted);
      margin: 0;
      font-size: 15px;
      line-height: 1.6;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .card {{
      background: rgba(18, 26, 47, 0.86);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 12px 32px rgba(0,0,0,0.22);
    }}

    .card-label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 10px;
    }}

    .card-value {{
      font-size: 30px;
      font-weight: 800;
    }}

    .section-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    h2 {{
      margin: 0 0 14px 0;
      font-size: 18px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 14px;
      font-size: 13px;
    }}

    th, td {{
      padding: 12px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}

    th {{
      color: var(--muted);
      text-align: left;
      background: rgba(255,255,255,0.04);
      font-weight: 600;
    }}

    tr:hover td {{
      background: rgba(255,255,255,0.035);
    }}

    .wide-card {{
      background: rgba(18, 26, 47, 0.86);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 12px 32px rgba(0,0,0,0.22);
      overflow-x: auto;
    }}

    .badge {{
      display: inline-block;
      padding: 5px 9px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}

    .success {{
      background: rgba(22,163,74,0.18);
      color: #86efac;
      border: 1px solid rgba(22,163,74,0.34);
    }}

    .danger {{
      background: rgba(220,38,38,0.18);
      color: #fca5a5;
      border: 1px solid rgba(220,38,38,0.34);
    }}

    .warning {{
      background: rgba(217,119,6,0.18);
      color: #fcd34d;
      border: 1px solid rgba(217,119,6,0.34);
    }}

    .neutral {{
      background: rgba(37,99,235,0.18);
      color: #93c5fd;
      border: 1px solid rgba(37,99,235,0.34);
    }}

    .footer {{
      color: var(--muted);
      margin-top: 24px;
      font-size: 13px;
      line-height: 1.6;
    }}

    code {{
      color: #ffd28a;
    }}

    @media (max-width: 900px) {{
      .grid,
      .section-grid {{
        grid-template-columns: 1fr;
      }}

      .page {{
        padding: 18px;
      }}

      h1 {{
        font-size: 26px;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>Vetri Voice Report</h1>
      <p class="subtitle">
        Local report generated from <code>voice/logs/voice_sessions.jsonl</code>.
        Generated at {safe_text(generated_at)}.
        This report is local-only and does not modify the Vetri Phase 3 core.
      </p>
    </section>

    <section class="grid">
      <div class="card">
        <div class="card-label">Total Sessions</div>
        <div class="card-value">{safe_text(total)}</div>
      </div>
      <div class="card">
        <div class="card-label">Successful Executions</div>
        <div class="card-value">{safe_text(success_count)}</div>
      </div>
      <div class="card">
        <div class="card-label">Blocked Attempts</div>
        <div class="card-value">{safe_text(blocked_count)}</div>
      </div>
      <div class="card">
        <div class="card-label">Failed/Error Sessions</div>
        <div class="card-value">{safe_text(error_count)}</div>
      </div>
    </section>

    <section class="grid">
      <div class="card">
        <div class="card-label">Average Duration</div>
        <div class="card-value">{safe_text(avg_duration)}s</div>
      </div>
      <div class="card">
        <div class="card-label">Latest Version</div>
        <div class="card-value">{safe_text(events[-1].get("version") if events else "N/A")}</div>
      </div>
      <div class="card">
        <div class="card-label">Latest Command</div>
        <div class="card-value" style="font-size:18px;">{safe_text(events[-1].get("matched_command") if events else "N/A")}</div>
      </div>
      <div class="card">
        <div class="card-label">Log Source</div>
        <div class="card-value" style="font-size:18px;">JSONL</div>
      </div>
    </section>

    <section class="section-grid">
      <div class="card">
        <h2>Status Breakdown</h2>
        <table>
          <thead><tr><th>Status</th><th>Count</th></tr></thead>
          <tbody>
            {render_counter_rows(status_counts, "No status data")}
          </tbody>
        </table>
      </div>

      <div class="card">
        <h2>Command Frequency</h2>
        <table>
          <thead><tr><th>Command</th><th>Count</th></tr></thead>
          <tbody>
            {render_counter_rows(command_counts, "No command data")}
          </tbody>
        </table>
      </div>

      <div class="card">
        <h2>Policy Risk Usage</h2>
        <table>
          <thead><tr><th>Risk</th><th>Count</th></tr></thead>
          <tbody>
            {render_counter_rows(risk_counts, "No risk data")}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section-grid">
      <div class="card">
        <h2>Version Breakdown</h2>
        <table>
          <thead><tr><th>Version</th><th>Count</th></tr></thead>
          <tbody>
            {render_counter_rows(version_counts, "No version data")}
          </tbody>
        </table>
      </div>

      <div class="card">
        <h2>Safety Notes</h2>
        <p class="subtitle">
          This report only reads local logs. It does not call OpenAI, execute commands,
          access Home Assistant, access Spotify, or modify backend files.
        </p>
      </div>

      <div class="card">
        <h2>Useful Commands</h2>
        <p class="subtitle">
          Generate report:<br>
          <code>python .\\voice\\voice_report.py</code><br><br>
          Open report:<br>
          <code>python .\\voice\\voice_report.py --open</code>
        </p>
      </div>
    </section>

    <section class="wide-card">
      <h2>Recent Voice Sessions</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Status</th>
            <th>Version</th>
            <th>Mode</th>
            <th>Heard</th>
            <th>Corrected</th>
            <th>Command</th>
            <th>Risk</th>
            <th>Summary</th>
          </tr>
        </thead>
        <tbody>
          {render_recent_rows(events, limit)}
        </tbody>
      </table>
    </section>

    <p class="footer">
      Vetri Voice V0H checkpoint. Current voice layer remains:
      Voice/Text → Safe Matcher → Policy Check → Vetri Phase 3 CLI → Local Summary → Local Logs.
    </p>
  </main>
</body>
</html>
"""


def write_report(events: list[dict[str, Any]], limit: int) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    html_content = build_html(events, limit=limit)

    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write(html_content)

    return REPORT_PATH


def open_report(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


def print_summary(events: list[dict[str, Any]], report_path: Path) -> None:
    summary = summarize_events(events)
    status_counts: Counter = summary["status_counts"]

    print()
    print("========================================")
    print(" Vetri Voice V0H - HTML Report")
    print("========================================")
    print(f"Log source:   {LOG_PATH}")
    print(f"Report file:  {report_path}")
    print(f"Sessions:     {summary['total']}")
    print(f"Success:      {status_counts.get('Success', 0)}")
    print(f"Blocked:      {status_counts.get('Blocked', 0)}")
    print(f"Failed/Error: {status_counts.get('Failed', 0) + status_counts.get('Error', 0)}")
    print(f"Avg duration: {summary['avg_duration']}s")
    print("========================================")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Vetri Voice HTML report.")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated report in the default browser.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of recent sessions to show in the report table.",
    )

    args = parser.parse_args()

    events = load_events()
    report_path = write_report(events, limit=args.limit)

    print_summary(events, report_path)

    if args.open:
        open_report(report_path)


if __name__ == "__main__":
    main()
