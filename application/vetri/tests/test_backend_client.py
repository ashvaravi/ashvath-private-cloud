from vetri_ai.clients.backend_client import BackendClient


def test_backend_allowlist_blocks_unknown_endpoint():
    result = BackendClient("http://127.0.0.1:1").safe_get("/not-allowed")
    assert result["status"] == "blocked"
