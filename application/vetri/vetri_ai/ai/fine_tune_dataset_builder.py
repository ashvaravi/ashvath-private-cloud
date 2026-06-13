from __future__ import annotations

from pathlib import Path


class FineTuneDatasetBuilder:
    """Future scaffold only. No upload or API fine-tuning call is implemented."""

    PURPOSE = {
        "rag": "knowledge",
        "fine_tuning": "behavior/style",
        "safety_router": "permission"
    }

    def build_placeholder(self, output_path: Path) -> dict[str, object]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        return {"ok": True, "message": "Empty fine-tuning dataset scaffold created. No upload performed."}
