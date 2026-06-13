from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vetri_ai.memory.memory_manager import MemoryManager


if __name__ == "__main__":
    print(MemoryManager().cleanup_by_retention_policy())
