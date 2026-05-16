---
name: aftertone-speed
description: Set Aftertone TTS playback speed in speak_summary.toml
---

If the user did not give a speed value, ask once (recommended range **0.9–1.5**, allowed **0.5–2.0**).

Run **only** from the **repository root** (replace `VALUE`):

```bash
uv run --directory py python speak_summary_config.py set speed VALUE
```

Report stdout. No daemon restart needed. No manual TOML edits.
