## Aftertone — agent map

- **Goal:** post-reply **local TTS** for coding agents (Cursor today; Claude & Codex adapters tracked in [CONTRIBUTING.md](CONTRIBUTING.md)).
- **`.cursor/hooks.json`** — Cursor adapter; must include `"version": 1`.
- **`.cursor/hooks/`** — `speak_summary.sh`, `speak_summary.toml`, `README.md` (full TOML reference), `hook_payload_trace.sh`.
- **`py/`** — `tts_daemon.py`, `tts_daemon_ctl.py`, `speak_summary_prepare.py`, vendored `helper.py` (Supertonic), `tts_io.py`, `fetch_assets.py`, diagnostics.
- **`scripts/bootstrap.sh`** — `uv sync` + HF snapshot if ONNX dir missing.

## Commands

- Bootstrap: `bash scripts/bootstrap.sh` from repo root.
- Daemon: `cd py && uv run python tts_daemon_ctl.py start --repo-root ..`
- `uv run` examples: `cd py` first, or `uv run --directory py …` from repo root.

## Env

- **`AFTERTONE_REPO`** — preferred repo root for hooks/daemon (set by `speak_summary.sh`).
- **`SUPERTONIC_REPO`** — legacy alias (same path; older forks).

## Facts

- Assets: Hugging Face `Supertone/supertonic-3` via `fetch_assets.py` → `./assets/`.
- Cursor hooks are **per workspace** `.cursor/`. User-wide hooks live under `~/.cursor/` (different layout).

## Cursor spoken summaries (`afterAgentResponse` + `tts_daemon`)

- **Reference:** [.cursor/hooks/README.md](.cursor/hooks/README.md) — every `speak_summary.toml` key, valid `lang` codes, heuristics, `quiet_hours`, **start / stop / status / restart**, when to restart the daemon.
- **Flow:** Cursor **`afterAgentResponse`** runs [.cursor/hooks/speak_summary.sh](.cursor/hooks/speak_summary.sh) → [py/speak_summary_prepare.py](py/speak_summary_prepare.py) (inline `text` from the hook; `stop` often has no useful transcript) → `POST` [py/tts_daemon.py](py/tts_daemon.py). Models stay loaded in the daemon.
- **Config:** [.cursor/hooks/speak_summary.toml](.cursor/hooks/speak_summary.toml) — **`voice_type`** / **`voice_style`**, **`lang`**, **`speed`**, **`total_step`**, `use_gpu`, `quiet_hours`, `min_chars`, **`max_chars`**, heuristic keys, `mode`, `enabled`.
- **Control:** `cd py && uv run python tts_daemon_ctl.py {start|stop|status|restart} --repo-root ..` — PID/port under `.cursor/hooks/state/`.
- **Toml vs running daemon:** **`port`**, **`onnx_dir`**, **`voice_*`**, **`use_gpu`** need **`restart`**. The hook posts to **`state/tts-daemon.port`**; mismatch with TOML logs **`port_mismatch`** in `speak_summary-hook.log`. **`status`** prints TOML on disk + healthz.
- **Registration:** [.cursor/hooks.json](.cursor/hooks.json) — **`"version": 1`**. **`afterAgentResponse`** → `speak_summary.sh`. Do not add unsupported keys (e.g. `workspaceOpen` in some builds). If the workspace root is **`py/`**, use [py/.cursor/hooks.json](py/.cursor/hooks.json) if present.
- **Verify hooks:** `bash py/diagnose_speak_hooks.sh` or `tail` `hook_payload_trace.jsonl` — look for `afterAgentResponse` and `inline_after_response_ok: true`.
- **Testing:** `SPEAK_SUMMARY_IGNORE_QUIET=1` skips `quiet_hours` in `speak_summary_prepare.py`.
- **If nothing speaks:** (1) `bash py/test_speak_summary_pipeline.sh` after `cd py && uv sync`. (2) Cursor **Settings → Hooks** without errors. (3) **Trusted** workspace. (4) `tail` `speak_summary-hook.log` and `speak_summary-prepare.stderr.log`. (5) `quiet_hours` or set `SPEAK_SUMMARY_IGNORE_QUIET=1`.
- **What gets spoken:** prefers `<spoken_summary>`; else **up to N sentences** with soft-opener skip and **code-heavy** fence handling (`heuristic_*` in TOML). **`lang`** is sent on every `/say`; the tag should use the **same natural language** as TOML `lang` — [.cursor/rules/spoken-summary.mdc](.cursor/rules/spoken-summary.mdc).
