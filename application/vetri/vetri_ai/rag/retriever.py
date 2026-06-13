from __future__ import annotations

from pathlib import Path

from vetri_ai.settings import ROOT_DIR


SAFE_PATTERNS = [
    "config/private_cloud_architecture.json",
    "data/project_memory/private_cloud_architecture.md",
    "data/project_memory/architecture_decisions.jsonl",
    "data/project_memory/completed_phases.jsonl",
    "data/incident_memory/incidents.jsonl",
    "data/daily_summaries/latest_daily_summary.json"
]


class KeywordRetriever:
    def __init__(self, root: Path = ROOT_DIR) -> None:
        self.root = root

    def source_paths(self) -> list[Path]:
        paths = [self.root / pattern for pattern in SAFE_PATTERNS]
        paths.extend((self.root / "data" / "cleaned_events").glob("*.jsonl"))
        paths.extend((self.root / "data" / "raw_imports" / "mac_exports").glob("*.json"))
        paths.extend((self.root / "data" / "raw_imports" / "mac_exports").glob("*.jsonl"))
        voice_memory = self.root / "voice" / "memory"
        if voice_memory.exists():
            paths.extend(voice_memory.glob("*.json"))
        return [path for path in paths if path.exists() and ".env" not in str(path).lower() and "legacy" not in str(path).lower()]

    def search(self, query: str, limit: int = 5) -> list[dict[str, object]]:
        terms = [term for term in query.lower().split() if len(term) > 2]
        results: list[dict[str, object]] = []
        for path in self.source_paths():
            text = path.read_text(encoding="utf-8", errors="replace")
            lowered = text.lower()
            score = sum(lowered.count(term) for term in terms)
            if score:
                snippet_start = min([lowered.find(term) for term in terms if term in lowered] or [0])
                snippet = text[max(0, snippet_start - 120):snippet_start + 600]
                results.append({"path": str(path), "score": score, "snippet": snippet})
        return sorted(results, key=lambda item: int(item["score"]), reverse=True)[:limit]
