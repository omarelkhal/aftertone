# /aftertone-on

Enable Aftertone spoken TTS for this Codex session only.

Codex does not document arbitrary custom slash commands as the primary extension point. Prefer `$aftertone-on`, or open `/skills` and choose `aftertone-on`.

Run exactly one command from the Aftertone install root:

```bash
uv run --directory py python -m aftertone on
```

Then include a short `<spoken_summary>` in this reply so the Codex `Stop` hook can register this session id on the allowlist. Other Codex sessions stay silent until enabled there too.

Terminal fallback without a Codex turn:

```bash
uv run --directory ~/aftertone/py python -m aftertone on
```
