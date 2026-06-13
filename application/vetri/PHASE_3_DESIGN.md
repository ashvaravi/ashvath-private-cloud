# Vetri AI Phase 3 Design Lock

## Status

Phase 3.0 is the OpenAI Safety Design Lock.

No OpenAI API call is implemented in this phase.

## Core Rule

OpenAI understands, explains, reasons, and suggests.

Local Vetri code validates, allows, blocks, and executes only approved actions.

The Mac executes only predefined approved backend actions or scripts.

## Why Phase 3 Exists

Phase 1B gave Vetri a safe command router.

Phase 2 gave Vetri read-only diagnosis workflows.

Phase 3 adds OpenAI as a reasoning and explanation layer.

OpenAI must not become the executor.

## Final Control Boundary

User
?
Local Vetri router
?
Safety router
?
Optional OpenAI reasoning over sanitized context
?
Local Vetri validation
?
Approved backend API call only
?
Mac execution server

## What OpenAI Can Do

OpenAI can:

- Explain diagnosis results
- Explain status summaries
- Convert technical output into simple language
- Recommend safe next checks
- Ask clarifying questions
- Suggest structured intent JSON
- Help reason over sanitized context packets

## What OpenAI Cannot Do

OpenAI cannot:

- Execute shell commands
- Execute SSH commands
- Call the backend directly
- Call Home Assistant directly
- Modify files
- Delete data
- Restart services directly
- Run backups directly
- Read secrets
- Read raw logs
- Access photos/videos
- Access database dumps
- Control devices directly

## Data Allowed to OpenAI

Allowed:

- User question
- Sanitized diagnosis result
- Sanitized status summary
- Allowed action names
- Service names
- Risk labels
- Safe project architecture summary
- Non-sensitive error summaries
- Safe recent findings

## Data Blocked from OpenAI

Never send:

- `.env`
- API keys
- Passwords
- Tokens
- SSH keys
- Home Assistant token
- Tailscale auth keys
- Raw full logs
- Photos/videos
- Immich database
- Database dumps
- Backup archives
- CCTV feeds
- Raw Home Assistant event firehose
- Full personal conversation history

## Phase 3 Mini-Phases

| Mini-Phase | Name | Purpose |
|---|---|---|
| 3.0 | OpenAI Safety Design Lock | Create policy and design rules |
| 3.1 | OpenAI config + client skeleton | Add safe OpenAI client, no execution |
| 3.2 | Sanitized context packet builder | Build safe packets from Vetri results |
| 3.3 | Explain diagnosis with OpenAI | Explain diagnosis results clearly |
| 3.4 | OpenAI intent suggestion mode | Let OpenAI suggest intent JSON |
| 3.5 | Local safety validation of OpenAI intent | Vetri validates suggested intent |
| 3.6 | Final Phase 3 checkpoint | Smoke test and documentation |

## Phase 3.1 Planned Scope

Phase 3.1 should only create:

- `vetri_ai/ai/openai_client.py`
- `vetri_ai/ai/prompt_builder.py`
- `vetri_ai/ai/context_packet.py`
- OpenAI config loading
- Safe disabled-by-default mode

OpenAI should not execute actions.

## Future Home Assistant Goal

Vetri is not only a troubleshooting assistant.

The final long-term goal is for Vetri to become the AI orchestration layer over Home Assistant, eventually usable like an Alexa-style voice assistant.

However, Home Assistant control must come later through:

- Device registry
- Entity allowlist
- Action allowlist
- Risk levels
- Confirmation gates
- Read-only state checks before control
- Post-action verification
- Audit logging

Home Assistant controls devices.

Vetri reasons, routes, validates, confirms, and explains.

## Final Phase 3 Rule

OpenAI may advise.

Local Vetri decides.

Backend executes only approved actions.
