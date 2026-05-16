---
name: aftertone-toggle
description: Toggle Aftertone spoken summary TTS on or off
---

Run **only** this shell command from the **repository root** (Aftertone workspace). Do not edit TOML by hand.

```bash
uv run --directory py python speak_summary_toggle.py toggle
```

Report the single line of stdout (`on` or `off`). If the command fails, show stderr. Do not make unrelated file changes.
