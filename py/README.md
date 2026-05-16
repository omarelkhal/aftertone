# Aftertone — Python

Inference stack + HTTP daemon for **Aftertone** (see [repository README](../README.md)).

```bash
cd py
uv sync
uv run python tts_daemon_ctl.py start --repo-root ..
```

Models: `bash ../scripts/bootstrap.sh` or `uv run --with huggingface_hub python fetch_assets.py`.

## Spoken summaries (Cursor + `tts_daemon`)

**Full TOML + daemon guide:** [.cursor/hooks/README.md](../.cursor/hooks/README.md).

After each assistant message, a Cursor **`afterAgentResponse`** hook can call the **local HTTP daemon** so ONNX loads once and `POST /say` stays fast.

1. **Config:** [.cursor/hooks/speak_summary.toml](../.cursor/hooks/speak_summary.toml) — `port`, **`voice_type`** / **`voice_style`**, **`lang`**, **`speed`**, **`total_step`**, `use_gpu`, `quiet_hours`, `min_chars`, **`max_chars`**, **`heuristic_*`**, `mode`, `enabled`.
2. **Hook:** [.cursor/hooks/speak_summary.sh](../.cursor/hooks/speak_summary.sh) → [speak_summary_prepare.py](speak_summary_prepare.py) → `POST` `/say` with `text`, `speed`, `lang`, `totalStep`, `mode`.
3. **Register:** [.cursor/hooks.json](../.cursor/hooks.json) — `afterAgentResponse` with matcher `AgentResponse`.
4. **Disable:** `enabled = false` in `speak_summary.toml`, or remove the hook entry.

**Daemon CLI**

```bash
cd py
uv run python tts_daemon_ctl.py status --repo-root ..
uv run python tts_daemon_ctl.py restart --repo-root ..
```

**Verify:** `bash py/test_speak_summary_pipeline.sh` (must print `OK:`). With a real agent reply: `bash py/diagnose_speak_hooks.sh`.
