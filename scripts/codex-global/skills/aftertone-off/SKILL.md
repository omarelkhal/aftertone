---
name: aftertone-off
description: Disable Aftertone spoken TTS for the current Codex chat session only.
---

# Aftertone Off

Disable spoken TTS for this Codex session only.

Run exactly one shell command:

```bash
root="$(cat ~/.cursor/hooks/aftertone-install-dir 2>/dev/null || printf '%s\n' "$HOME/aftertone")"; uv run --directory "$root/py" python -m aftertone off
```

Then end the reply with one short `<spoken_summary>` block so the Codex `Stop` hook can remove this session id from the allowlist. Other Codex sessions are unchanged.
