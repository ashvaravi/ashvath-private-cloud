from __future__ import annotations

from pathlib import Path

from vetri_ai.rag.retriever import KeywordRetriever
from vetri_ai.settings import ROOT_DIR


class RAGEngine:
    def __init__(self, root: Path = ROOT_DIR) -> None:
        self.retriever = KeywordRetriever(root)

    def retrieve(self, query: str, limit: int = 5) -> list[dict[str, object]]:
        return self.retriever.search(query, limit)

    def answer_from_memory(self, query: str) -> str:
        hits = self.retrieve(query)
        if not hits:
            return "I do not have a grounded memory entry for that yet."
        lines = ["Relevant local memory:"]
        for hit in hits:
            lines.append(f"- {hit['path']}: {str(hit['snippet']).strip()[:220]}")
        return "\n".join(lines)
