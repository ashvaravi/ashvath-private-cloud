from __future__ import annotations

from vetri_ai.rag.rag_engine import RAGEngine


def build_relevant_context(query: str) -> list[dict[str, object]]:
    return RAGEngine().retrieve(query)
