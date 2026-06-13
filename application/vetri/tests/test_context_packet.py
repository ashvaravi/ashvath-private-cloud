from vetri_ai.ai.context_packet import build_context_packet


def test_context_redacts_secret_values():
    packet = build_context_packet("hello", latest_status_summary={"token": "abc123"})
    assert "abc123" not in str(packet)
