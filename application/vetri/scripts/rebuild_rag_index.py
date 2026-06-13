from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vetri_ai.rag.index_builder import rebuild_index


if __name__ == "__main__":
    print(rebuild_index())
