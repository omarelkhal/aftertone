# /aftertone-status

Show Aftertone config, daemon state, and enabled session ids.

Codex does not document arbitrary custom slash commands as the primary extension point. Prefer `$aftertone-status`, or open `/skills` and choose `aftertone-status`.

Run exactly one command from the Aftertone install root:

```bash
uv run --directory py python -m aftertone status
```
