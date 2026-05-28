---
name: aftertone-on
description: Enable Aftertone spoken TTS for the current Codex chat session only.
---

# Aftertone On

Enable spoken TTS for this Codex session only.

Run exactly one shell command:

```bash
root="$(cat ~/.cursor/hooks/aftertone-install-dir 2>/dev/null || printf '%s\n' "$HOME/aftertone")"; uv run --directory "$root/py" python -m aftertone on
```

Then end the reply with one short `<spoken_summary>` block so the Codex `Stop` hook can register this session id on the allowlist. Other Codex sessions stay silent until enabled there too.
