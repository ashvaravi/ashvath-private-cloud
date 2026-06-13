from __future__ import annotations


class FTSEngine:
    def search(self, query: str) -> list[dict[str, object]]:
        return [{"status": "placeholder", "query": query, "message": "SQLite FTS scaffold is present; keyword retrieval remains primary."}]
