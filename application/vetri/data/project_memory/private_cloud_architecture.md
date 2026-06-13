# Ashvath Private Cloud + Vetri AI Architecture

Windows is the AI brain and stable local voice runtime. The MacBook is the execution server. The Mac FastAPI backend is the primary control gateway for private cloud state, diagnostics, backup visibility, network status, dashboard summaries, and Home Assistant.

The stable terminal voice assistant stays in `Z:\HomeLLM\voice`. It uses openWakeWord with the current phrase `hey jarvis`, opens a short command window after wake, ignores silence/noise/random speech, and returns to wake-only mode after commands. Local Windows TTS speaks summaries. Spotify is controlled through the Spotify Web API from Windows.

Home Assistant control must always go through the Mac backend. Windows never directly calls Home Assistant and never stores or exposes the Home Assistant token. The backend verifies device state after control requests.

OpenAI is used only for reasoning, explanation, planning, and conversation when explicitly enabled. Local Vetri code owns safety, policy, permission checks, memory decisions, routing, and execution. OpenAI receives only sanitized context packets and cannot execute commands.

Mac exports are the operational truth source for Windows AI memory and RAG. Windows consumes only the safe export folder at `~/Ashvath-private-cloud/exports/for-vetri-ai`, synced into `Z:\HomeLLM\data\raw_imports\mac_exports`.

The core operating loop is: user request, intent classification, confidence scoring, policy engine, risk classification, confirmation gate if needed, approved backend action only, execution, post-action verification, audit log, summary, optional memory update.

Completed checkpoints include Mac backend version 1.0.0 locked and healthy, backend/frontend/private cloud foundation completed, Home Assistant backend gateway working, wake-word stability passed, local Windows TTS passed, Spotify voice routing passed, Spotify memory/regional work started, and Mac safe export layer completed and validated.

Regional Spotify search needs stronger NLP: Unicode-safe normalization, transliteration aliases, title guards, memory correction, and better STT handling for music commands. Tamil text must not be stripped.
