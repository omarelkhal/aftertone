# /prompts:aftertone-off

Disable Aftertone spoken TTS for this Codex session only.

Prefer `$aftertone-off`, or open `/skills` and choose `aftertone-off`. This prompt remains a compatibility fallback.

Run exactly one shell command:

```bash
root="$(cat ~/.cursor/hooks/aftertone-install-dir 2>/dev/null || printf '%s\n' "$HOME/aftertone")"; uv run --directory "$root/py" python -m aftertone off
```

Then include a short `<spoken_summary>` tag in this reply so the Codex `Stop` hook can remove this session id from the allowlist.
