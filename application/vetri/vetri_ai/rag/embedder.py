from __future__ import annotations


class Embedder:
    enabled = False

    def embed(self, _text: str) -> list[float]:
        return []
