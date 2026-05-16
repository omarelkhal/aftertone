---
name: aftertone-restart
description: Restart Aftertone TTS daemon (voice, port, ONNX, GPU)
---

Run **only** these commands. Do not edit TOML or hand-kill processes.

```bash
AFTERTONE_ROOT="$(bash "${HOME}/.cursor/hooks/aftertone-root.sh" 2>/dev/null || echo "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
cd "${AFTERTONE_ROOT}/py" && uv run python tts_daemon_ctl.py restart --repo-root ..
uv run --directory "${AFTERTONE_ROOT}/py" python tts_daemon_ctl.py status --repo-root ..
```

Report the **restart** line (started pid/port) and the **status** block (running, port, voice, `ready`). If restart fails, show stderr and suggest `uv sync` in `py/` or `/aftertone-status`.

**When restart is required:** `port`, `onnx_dir`, `voice_type` / `voice_style`, `use_gpu`. **No restart** for `lang`, `speed`, `total_step`, `enabled`, `expression_mode`, or heuristics — those apply on the next hook.
