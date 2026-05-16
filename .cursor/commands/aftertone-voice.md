---
name: aftertone-voice
description: Set Aftertone voice preset and optionally restart the TTS daemon
---

Voice changes require a **daemon restart** to load new ONNX voice JSON.

1. If the user did not name a preset, list available presets:

```bash
uv run --directory py python speak_summary_config.py voices
```

(Presets come from `assets/voice_styles/*.json`; run `bash scripts/bootstrap.sh` if empty.)

2. Apply the voice (replace `PRESET` with e.g. `M1`, `F2`):

```bash
uv run --directory py python speak_summary_config.py set voice PRESET --restart
```

Use `--restart` so the new voice loads immediately. If the user only wanted to set TOML without restart, omit `--restart` and tell them to run `cd py && uv run python tts_daemon_ctl.py restart --repo-root ..`.

Report command output only; do not hand-edit TOML.
