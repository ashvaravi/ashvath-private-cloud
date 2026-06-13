from __future__ import annotations


class HomeAssistantClient:
    """Placeholder documenting the backend-first Home Assistant rule."""

    def direct_call(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        return {"ok": False, "status": "blocked", "message": "Windows direct Home Assistant calls are forbidden. Use Mac backend verified endpoints."}
