---
name: aftertone-mode
description: Set Aftertone TTS queue mode (queue or interrupt)
---

If the user did not specify, ask: **`queue`** (wait for current speech) or **`interrupt`** (stop and speak new line).

Run **only** from the **repository root** (replace `MODE` with `queue` or `interrupt`):

```bash
uv run --directory py python speak_summary_config.py set mode MODE
```

Report stdout. No daemon restart needed.
