---
name: aftertone-status
description: Show Aftertone spoken TTS and speak_summary.toml settings
---

Run these from the **repository root** and summarize the output for the user:

```bash
uv run --directory py python speak_summary_config.py status
uv run --directory py python speak_summary_toggle.py status
cd py && uv run python tts_daemon_ctl.py status --repo-root ..
```

Do not change files unless the user asked for a change. Explain whether spoken TTS is on, current `lang` / `speed` / `mode` / voice, and whether the daemon is running.
