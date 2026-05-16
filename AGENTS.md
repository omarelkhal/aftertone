## Aftertone — agent map

**This repository** (`https://github.com/omarelkhal/aftertone`) is the **default project** for Cursor/agent work (spoken TTS, hooks, daemon). Do not confuse it with the upstream **`supertone-inc/supertonic`** clone unless the user is contributing to Supertonic itself.

- **Goal:** post-reply **local TTS** for coding agents (Cursor today; Claude & Codex adapters tracked in [CONTRIBUTING.md](CONTRIBUTING.md)).
- **`.cursor/hooks.json`** — Cursor adapter; must include `"version": 1`.
- **`.cursor/hooks/`** — `speak_summary.sh`, `speak_summary.toml`, `README.md` (full TOML reference), `hook_payload_trace.sh`.
- **`py/`** — `tts_daemon.py`, `tts_daemon_ctl.py`, `speak_summary_prepare.py`, `speak_summary_toggle.py` (flip `enabled` in TOML), `speak_summary_config.py` (lang/speed/mode/voice), vendored `helper.py` (Supertonic), `tts_io.py`, `fetch_assets.py`, diagnostics.
- **`.cursor/commands/`** — **only user-facing way** to change spoken-TTS settings (`/aftertone-toggle`, `/aftertone-lang`, …). Agent runs `speak_summary_toggle.py` / `speak_summary_config.py`; do not hand-edit TOML or suggest VS Code tasks for config.
- **`scripts/bootstrap.sh`** — `uv sync` + HF snapshot if ONNX dir missing.

## Commands

- One-line install: `curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash` (see `scripts/install.sh`).
- Bootstrap: `bash scripts/bootstrap.sh` from repo root.
- Daemon: `cd py && uv run python tts_daemon_ctl.py start --repo-root ..`
- **User config:** slash `/aftertone-*` only ([`.cursor/commands/`](.cursor/commands/)). When the user wants to change TTS settings, run the matching command’s scripts — do not tell them to edit TOML or use terminal CLIs directly. **lang/speed/mode/voice** without a value: **AskQuestion** first (see each command file); **voice** uses `set voice … --restart --ensure`. Open the **repo root** as the workspace so commands load (opening only `py/` still works for hooks via [py/.cursor/hooks.json](py/.cursor/hooks.json) if present).
- Tests: `cd py && uv sync && uv run pytest` — `py/tests/` (integration tests run `speak_summary_prepare.py` with temp TOML; unit tests cover helpers including quiet hours).
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
- **Config:** [.cursor/hooks/speak_summary.toml](.cursor/hooks/speak_summary.toml) — **`voice_type`** / **`voice_style`**, **`lang`**, **`speed`**, **`total_step`**, `use_gpu`, `quiet_hours`, `min_chars`, **`max_chars`**, **`spoken_summary_max_chars`**, **`heuristic_max_chars`**, **`plain_excerpt_max_chars`**, heuristic keys, **`only_speak_spoken_summary`**, `mode`, `enabled`.
- **Control:** `cd py && uv run python tts_daemon_ctl.py {start|stop|status|restart} --repo-root ..` — PID/port under `.cursor/hooks/state/`.
- **Toml vs running daemon:** **`port`**, **`onnx_dir`**, **`voice_*`**, **`use_gpu`** need **`restart`**. The hook posts to **`state/tts-daemon.port`**; mismatch with TOML logs **`port_mismatch`** in `speak_summary-hook.log`. **`status`** prints TOML on disk + healthz.
- **Registration:** [.cursor/hooks.json](.cursor/hooks.json) — **`"version": 1`**. **`afterAgentResponse`** → `speak_summary.sh`. Do not add unsupported keys (e.g. `workspaceOpen` in some builds). If the workspace root is **`py/`**, use [py/.cursor/hooks.json](py/.cursor/hooks.json) if present.
- **Verify hooks:** `bash py/diagnose_speak_hooks.sh` or `tail` `hook_payload_trace.jsonl` — look for `afterAgentResponse` and `inline_after_response_ok: true`.
- **Testing:** `SPEAK_SUMMARY_IGNORE_QUIET=1` skips `quiet_hours` in `speak_summary_prepare.py`. After changing **`lang`** in `speak_summary.toml`, from repo root run `uv run --directory py python sync_spoken_rule_lang.py` so `.cursor/rules/spoken-summary.mdc` stays aligned (Cursor rules do not read TOML at runtime).
- **If nothing speaks:** (1) `bash py/test_speak_summary_pipeline.sh` after `cd py && uv sync`. (2) Cursor **Settings → Hooks** without errors. (3) **Trusted** workspace. (4) `tail` `speak_summary-hook.log` and `speak_summary-prepare.stderr.log`. (5) `quiet_hours` or set `SPEAK_SUMMARY_IGNORE_QUIET=1`.
- **What gets spoken:** [py/speak_summary_prepare.py](py/speak_summary_prepare.py) prefers `<spoken_summary>...</spoken_summary>` (markdown-stripped, **leading sentences only**, capped by **`spoken_summary_max_chars`**, default 360); otherwise up to **N** heuristic sentences capped by **`heuristic_max_chars`** (default 480). Plain excerpt uses **`plain_excerpt_max_chars`**. **Code-heavy** replies use fewer sentences (`heuristic_code_fence_fraction`, `heuristic_max_sentences_code_heavy`). **`lang` in TOML** is both the ONNX language code and the **language the spoken string should be written in**; there is **no auto-translation**. Set **`only_speak_spoken_summary = true`** to disable heuristics. See [.cursor/rules/spoken-summary.mdc](.cursor/rules/spoken-summary.mdc).
- **Code-only or mostly-fenced replies:** prepare replaces fenced blocks with a short placeholder for fallbacks so TTS can still run; best quality is still a real `<spoken_summary>` line.
