# /aftertone-off

Disable Aftertone spoken TTS for this Codex session only.

Run exactly one command from the Aftertone install root:

```bash
uv run --directory py python -m aftertone off
```

The next Codex `Stop` hook with this session id clears it from the allowlist. Other sessions are unchanged.

Terminal fallback without a Codex turn:

```bash
uv run --directory ~/aftertone/py python -m aftertone off
```
