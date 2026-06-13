from __future__ import annotations

from pathlib import Path

from vetri_ai.rag.retriever import KeywordRetriever
from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import append_jsonl, save_json
from vetri_ai.utils.time_utils import now_iso


def rebuild_index(root: Path = ROOT_DIR) -> dict[str, object]:
    chunks_path = root / "data" / "rag_store" / "chunks.jsonl"
    chunks_path.write_text("", encoding="utf-8")
    count = 0
    for path in KeywordRetriever(root).source_paths():
        text = path.read_text(encoding="utf-8", errors="replace")
        append_jsonl(chunks_path, {"path": str(path), "text": text[:4000]})
        count += 1
    save_json(root / "data" / "rag_store" / "metadata.json", {"backend": "local_keyword_search", "embeddings_enabled": False, "last_rebuild": now_iso(), "sources": count})
    return {"ok": True, "sources": count}
