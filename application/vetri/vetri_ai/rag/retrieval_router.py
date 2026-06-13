from __future__ import annotations

from vetri_ai.rag.rag_engine import RAGEngine


def retrieve_safe_context(query: str) -> list[dict[str, object]]:
    return RAGEngine().retrieve(query)
