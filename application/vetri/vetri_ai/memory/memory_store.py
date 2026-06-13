from __future__ import annotations

from pathlib import Path
from typing import Any

from vetri_ai.memory.memory_policy import can_store_memory, importance_for
from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import append_jsonl, read_jsonl
from vetri_ai.utils.time_utils import now_iso


class MemoryStore:
    def __init__(self, root: Path = ROOT_DIR) -> None:
        self.root = root
        self.personal_path = root / "data" / "personal_memory" / "rich_personal_memory.jsonl"
        self.tombstone_path = root / "data" / "personal_memory" / "memory_tombstones.jsonl"
        self.conversation_dir = root / "data" / "conversation_summaries"
        self.conversation_dir.mkdir(parents=True, exist_ok=True)

    def remember(self, text: str, source: str = "explicit") -> dict[str, Any]:
        allowed, reason = can_store_memory(text)
        if not allowed:
            return {"ok": False, "reason": reason}
        item = {
            "timestamp": now_iso(),
            "source": source,
            "importance": importance_for(text),
            "text": text,
            "retention": "user_controlled"
        }
        append_jsonl(self.personal_path, item)
        return {"ok": True, "memory": item}

    def review(self, limit: int = 12) -> list[dict[str, Any]]:
        return read_jsonl(self.personal_path, limit=limit)

    def tombstone(self, query: str) -> dict[str, Any]:
        item = {"timestamp": now_iso(), "query": query, "reason": "user_forget_request"}
        append_jsonl(self.tombstone_path, item)
        return {"ok": True, "tombstone": item}

    def summarize_review(self) -> str:
        rows = self.review()
        if not rows:
            return "I do not have rich personal memory saved yet."
        lines = ["Personal memory review:"]
        for row in rows:
            lines.append(f"- [{row.get('importance')}] {row.get('text')}")
        return "\n".join(lines)
