# Vetri AI Phase 3.2 Checkpoint

## Status

Phase 3.2 integrates sanitized context packet preview.

No OpenAI API call is made in this phase.

## Added Behavior

New commands:

- `preview context immich`
- `preview context backup`
- `preview context storage`
- `preview context network`
- `preview context backend`
- `preview context frontend`

Debug examples:

- `json preview context immich`
- `json preview context backup`

## Purpose

This phase verifies what OpenAI would see later.

The packet excludes:

- Raw backend results
- Secrets
- API keys
- Tokens
- Raw logs
- Photos/videos
- Database dumps
- Backup archives
- SSH keys

## Flow

User asks for context preview
?
Vetri runs read-only diagnosis
?
ContextPacketBuilder sanitizes the result
?
Vetri shows safe packet preview
?
No OpenAI call is made

## Next Phase

Phase 3.3: Explain diagnosis with OpenAI.

That phase will require adding the OpenAI API key and enabling OpenAI deliberately.
