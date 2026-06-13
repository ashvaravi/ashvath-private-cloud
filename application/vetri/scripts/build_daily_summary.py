from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vetri_ai.logs.daily_summarizer import build_daily_summary


if __name__ == "__main__":
    print(build_daily_summary())
