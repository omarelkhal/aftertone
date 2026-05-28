# /prompts:aftertone-on

Enable Aftertone spoken TTS for this Codex session only.

Run exactly one shell command:

```bash
root="$(cat ~/.cursor/hooks/aftertone-install-dir 2>/dev/null || printf '%s\n' "$HOME/aftertone")"; uv run --directory "$root/py" python -m aftertone on
```

Then include a short `<spoken_summary>` tag in this reply so the Codex `Stop` hook can register this session id on the allowlist.
