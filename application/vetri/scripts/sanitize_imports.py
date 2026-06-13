from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vetri_ai.logs.event_extractor import extract_mac_export_events


if __name__ == "__main__":
    result = extract_mac_export_events()
    print(result)
