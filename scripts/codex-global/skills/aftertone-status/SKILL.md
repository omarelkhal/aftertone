---
name: aftertone-status
description: Show Aftertone config, daemon state, and enabled Codex session ids.
---

# Aftertone Status

Show Aftertone config, daemon state, and enabled session ids.

Run exactly one shell command:

```bash
root="$(cat ~/.cursor/hooks/aftertone-install-dir 2>/dev/null || printf '%s\n' "$HOME/aftertone")"; uv run --directory "$root/py" python -m aftertone status
```
