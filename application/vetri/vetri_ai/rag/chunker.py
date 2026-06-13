from __future__ import annotations


def chunk_text(text: str, size: int = 900) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    for index in range(0, len(words), size):
        chunks.append(" ".join(words[index:index + size]))
    return chunks or ([text] if text else [])
