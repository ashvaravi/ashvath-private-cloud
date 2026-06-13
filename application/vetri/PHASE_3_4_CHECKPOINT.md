# Vetri AI Phase 3.4 Checkpoint

## Status

Phase 3.4 adds OpenAI intent suggestion mode.

OpenAI can suggest a structured intent from flexible user language.

## Added Command Patterns

- `openai intent why is immich slow`
- `suggest intent for backup looks wrong`
- `ai route frontend is not loading`
- `interpret request tailscale is not working`

## Execution Boundary

OpenAI suggests only.

Local Vetri validates.

No suggested intent is executed in Phase 3.4.

## Output

Phase 3.4 returns:

- OpenAI suggested intent
- Confidence
- Reason
- Local allowlist validation
- Risk/write-access information
- Execution status: false

## Still Blocked

- OpenAI execution
- Backend calls directly from OpenAI
- Home Assistant calls directly from OpenAI
- Restarts
- Backup execution
- File modification
- RAG
- Memory writes
- Voice
- Home Assistant control

## Next Phase

Phase 3.5: Local safety validation and optional execution of OpenAI-suggested read-only intents.

Phase 3.5 must only allow execution if:
- suggested intent is allowlisted
- intent is read-only
- risk is low
- confidence is high enough
- local Vetri safety router approves
