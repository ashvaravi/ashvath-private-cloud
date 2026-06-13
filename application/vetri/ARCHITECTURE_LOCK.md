# Vetri AI Architecture Lock

Vetri is the Windows-side AI brain for the Ashvath Private Cloud. The MacBook is the execution server and the FastAPI backend on Mac is the primary control gateway.

Core rule: Vetri should think conversationally, but act deterministically and safely.

## Roles

- Windows (`Z:\HomeLLM`) runs the stable terminal wake-word assistant and the new Vetri AI brain foundation.
- The stable voice folder remains at `Z:\HomeLLM\voice` and is not moved into `vetri_ai`.
- The current wake phrase remains `hey jarvis`.
- The future wake phrase is `Hey Vetri`, trained later with a custom openWakeWord model using Colab.
- Mac private cloud root is `~/Ashvath-private-cloud`.
- Mac backend root is `~/Ashvath-private-cloud/application/backend`.
- Mac exports sanitized operational truth into `~/Ashvath-private-cloud/exports/for-vetri-ai`.

## Execution Model

LLM suggests. Router validates. Tool executes. Backend verifies. Memory records.

OpenAI may be used later for reasoning, explanation, planning, and conversation. Local Vetri code controls safety, policy, permissions, memory, and execution decisions. OpenAI is disabled by default and never executes actions.

## Home Assistant

Windows must never directly call Home Assistant. Home Assistant control must go through the Mac FastAPI backend, where the token stays. The backend verifies final device state.

## Voice

The existing terminal-only openWakeWord assistant is stable and must not be rewritten during the AI brain foundation work. `vetri_ai\voice` is only a future integration wrapper for chat routing after CLI tests pass.

## Safety

High-risk operations remain blocked: deleting files, wiping volumes, changing firewall or Tailscale ACLs, editing SSH config, removing Docker volumes, exposing public ports, reading private media, uploading secrets, arbitrary shell execution, automatic package installs, Docker Compose edits, raw CCTV access, and mass log deletion without retention policy.

## Memory Lifecycle

Raw logs become cleaned events. Cleaned events become daily summaries. Important failures become incident memory. Summaries and incident memory become RAG chunks. Old low-value raw data expires.

Raw logs expire. Summaries survive. Incidents persist. Personal memory is user-controlled. Vector indexes are rebuildable.
