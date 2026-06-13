from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vetri_ai.monitoring.runner import format_monitoring_report, run_monitoring


if __name__ == "__main__":
    print(format_monitoring_report(run_monitoring()))
