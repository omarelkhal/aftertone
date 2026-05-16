# Aftertone — Python

Inference stack + HTTP daemon for **Aftertone** (see [repository README](../README.md)).

```bash
cd py
uv sync
uv run python tts_daemon_ctl.py start --repo-root ..
```

Models: `bash ../scripts/bootstrap.sh` or `uv run --with huggingface_hub python fetch_assets.py`.

## Spoken summaries (Cursor + `tts_daemon`)

**Full TOML + daemon guide:** [.cursor/hooks/README.md](../.cursor/hooks/README.md) (every key, languages, ranges, heuristics, `quiet_hours`, start/stop/restart).

After each assistant message, a [Cursor **`afterAgentResponse`** hook](https://cursor.com/docs/hooks) (matcher `AgentResponse`) can call the **local HTTP daemon** so ONNX loads once and `POST /say` stays fast. The older `stop` + transcript path is unreliable for TTS (often empty JSON or no `transcript_path`).

1. **Config:** [.cursor/hooks/speak_summary.toml](../.cursor/hooks/speak_summary.toml) — `port`, **`voice_type`** / **`voice_style`**, **`lang`**, **`speed`**, **`total_step`**, `use_gpu`, `quiet_hours`, `min_chars`, **`max_chars`**, **`spoken_summary_max_chars`**, **`heuristic_max_chars`**, **`plain_excerpt_max_chars`**, **`heuristic_max_sentences`** (1–3), **`heuristic_code_fence_fraction`**, **`heuristic_max_sentences_code_heavy`**, **`only_speak_spoken_summary`**, `mode` (`queue` or `interrupt`), `enabled`.
2. **Hook:** [.cursor/hooks/speak_summary.sh](../.cursor/hooks/speak_summary.sh) — reads hook JSON (uses inline `text` from `afterAgentResponse`), runs [speak_summary_prepare.py](speak_summary_prepare.py), `POST`s JSON to `http://127.0.0.1:<port>/say`.
3. **Register:** [.cursor/hooks.json](../.cursor/hooks.json) — `afterAgentResponse` → `speak_summary.sh` with matcher `AgentResponse` (not `afterAgentThought`). When the workspace is **`py/`** only, use [py/.cursor/hooks.json](.cursor/hooks.json) if present. State, logs, and TOML stay under **repo** `.cursor/hooks/`.
4. **On / off (spoken summaries):** `uv run python speak_summary_toggle.py on|off|toggle|status` from `py/` (or `uv run --directory py …` from repo root). Sets `enabled` in `speak_summary.toml`; applies on the next reply without restarting the daemon. Cursor tasks: [`.vscode/tasks.json`](../.vscode/tasks.json). See [Turn spoken TTS on or off](../README.md#turn-spoken-tts-on-or-off) in the repo README.
5. **Fully disable the hook:** remove the `afterAgentResponse` entry from `hooks.json` (rare; prefer `enabled = false`).
6. **Spoken-summary rule `lang`:** after changing **`lang`** in the TOML, from **repo root** run `uv run --directory py python sync_spoken_rule_lang.py` so [`.cursor/rules/spoken-summary.mdc`](../.cursor/rules/spoken-summary.mdc) shows the same code in the agent prompt (Cursor rules are static; they do not read TOML at runtime).

**Daemon CLI** (from `cd py`):

```bash
cd py
uv run python tts_daemon_ctl.py start --repo-root ..
uv run python tts_daemon_ctl.py status --repo-root ..
uv run python tts_daemon_ctl.py stop --repo-root ..
```

**Direct daemon** (logs to `.cursor/hooks/state/tts-daemon.log`; spoken lines append to `.cursor/hooks/state/spoken/YYYY-MM-DD.jsonl`):

```bash
cd py
uv run python tts_daemon.py --port 8765 --use-gpu
```

**Summaries:** the hook prefers `<spoken_summary>...</spoken_summary>` (markdown-stripped, leading sentences, capped by **`spoken_summary_max_chars`** in TOML). Otherwise sentence heuristics / plain excerpt use separate caps; see hooks README. After changing **`lang`**, run **`sync_spoken_rule_lang.py`** (step 5 above). Optional: set `SPEAK_SUMMARY_IGNORE_QUIET=1` when testing so `quiet_hours` does not skip output.

**Verify install:** from repo root, after `cd py && uv sync`, run `bash py/test_speak_summary_pipeline.sh` — must print `OK:` and exit 0. After a **real** Cursor agent reply, run `bash py/diagnose_speak_hooks.sh` and confirm `hook_payload_trace.jsonl` contains `afterAgentResponse` with `inline_after_response_ok: true`.

**Models without Git LFS:** from repo root run `bash scripts/bootstrap.sh` (or `cd py && uv run --with huggingface_hub python fetch_assets.py`) to populate `../assets/` from Hugging Face `Supertone/supertonic-3`.
