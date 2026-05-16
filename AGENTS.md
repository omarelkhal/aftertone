## Aftertone — agent map

**This repository** (`https://github.com/omarelkhal/aftertone`) is the **default project** for Cursor/agent work (spoken TTS, hooks, daemon). Do not confuse it with the upstream **`supertone-inc/supertonic`** clone unless the user is contributing to Supertonic itself.

- **Goal:** post-reply **local TTS** for coding agents (Cursor today; Claude & Codex adapters tracked in [CONTRIBUTING.md](CONTRIBUTING.md)).
- **`.cursor/hooks.json`** — Cursor adapter; must include `"version": 1`.
- **`.cursor/hooks/`** — `speak_summary.sh`, `speak_summary.toml`, `README.md` (full TOML reference), `hook_payload_trace.sh`.
- **`py/`** — `tts_daemon.py`, `tts_daemon_ctl.py`, `speak_summary_prepare.py`, `speak_summary_toggle.py` (flip `enabled` in TOML), `speak_summary_config.py` (lang/speed/mode/voice), vendored `helper.py` (Supertonic), `tts_io.py`, `fetch_assets.py`, diagnostics.
- **`.cursor/commands/`** — **only user-facing way** to change spoken-TTS settings (`/aftertone-toggle`, `/aftertone-lang`, …). Agent runs `speak_summary_toggle.py` / `speak_summary_config.py`; do not hand-edit TOML or suggest VS Code tasks for config.
- **`scripts/bootstrap.sh`** — `uv sync` + HF snapshot if ONNX dir missing.

## Commands

- One-line install: `curl -fsSL .../install.sh | bash -s -- --install-uv --start-daemon` → **`~/aftertone`** + **user hooks** in `~/.cursor/hooks.json` (default `--global`). Legacy per-project: `--no-global --into .`. See `scripts/install.sh`.
- Bootstrap: `bash scripts/bootstrap.sh` from repo root.
- Daemon: `cd py && uv run python tts_daemon_ctl.py start --repo-root ..`
- **User config:** slash `/aftertone-*` only ([`.cursor/commands/`](.cursor/commands/)). When the user wants to change TTS settings, run the matching command’s scripts — do not tell them to edit TOML or use terminal CLIs directly. **lang/speed/mode/voice** without a value: **AskQuestion** first (see each command file); **voice** uses `set voice … --restart --ensure`. Open the **repo root** as the workspace so commands load (opening only `py/` still works for hooks via [py/.cursor/hooks.json](py/.cursor/hooks.json) if present).
- Tests: `cd py && uv sync && uv run pytest` — `py/tests/` (integration tests run `speak_summary_prepare.py` with temp TOML; unit tests cover helpers including quiet hours).
- `uv run` examples: `cd py` first, or `uv run --directory py …` from repo root.

## Env

- **`AFTERTONE_REPO`** / **`AFTERTONE_INSTALL_DIR`** — install root (`~/aftertone` by default; `~/.cursor/hooks/aftertone-install-dir` after global install). Set by hooks or env.
- **`SUPERTONIC_REPO`** — legacy alias (same path; older forks).

## Facts

- Assets: Hugging Face `Supertone/supertonic-3` via `fetch_assets.py` → `./assets/`.
- **Global install (default):** user hooks `~/.cursor/hooks.json` → wrapper → `~/aftertone/.cursor/hooks/speak_summary.sh`. Config TOML + daemon state stay under **`~/aftertone/.cursor/hooks/`**. Slash commands copied to `~/.cursor/commands/`.
- **Legacy:** project `.cursor/hooks.json` via `install.sh --into` (duplicates `py/` per repo).

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
- **What gets spoken:** [py/speak_summary_prepare.py](py/speak_summary_prepare.py) prefers `<spoken_summary>...</spoken_summary>` (markdown-stripped, **leading sentences only**, capped by **`spoken_summary_max_chars`**, default 360). With **`only_speak_spoken_summary = true`** (repo default), **no tag → silence** — agents must write the tag on substantive replies. Heuristic fallbacks (when enabled) cap at **`heuristic_max_chars`** / **`plain_excerpt_max_chars`**. **`lang` in TOML** is both the ONNX language code and the **language the spoken string should be written in**; there is **no auto-translation**. Tag content should be a **flow briefing** (state, significance, steering when useful), not a changelog — see [.cursor/rules/spoken-summary.mdc](.cursor/rules/spoken-summary.mdc) and [.cursor/hooks/README.md § Spoken summary intent](.cursor/hooks/README.md).
- **Code-only or mostly-fenced replies:** prepare replaces fenced blocks with a short placeholder for fallbacks so TTS can still run; best quality is still a real `<spoken_summary>` line.

## Learned User Preferences

- **Spoken summaries** should sound like a **hybrid pair-programmer briefing** for vibe coding: lead with **state** (what happened), add **significance** when it changes what to think, add a **next move** only for blockers, risk, tests, decisions, or clear actions — calm, direct tone; no file paths or filler in `<spoken_summary>`. For **livelier Supertonic delivery**, end **each sentence** inside the tag with `!!`, `??`, `?!`, or `!?` (vary them); do **not** use `state="..."` on the tag — inline expression tags were too subtle to hear.
- Voice pickers and status should show **human names with gender**, e.g. `Sara (female)` / `James (male)` (`py/voice_presets.py`); TOML still uses `M1`/`F4` ids.
- Public README and site adapter tables should list only **Cursor, Claude Code, Codex, and OpenCode** (not other agent brands).
- **Do not propose or integrate Microsoft VibeVoice**; user evaluated it locally and declined (heavy runtime vs staying on Supertonic ONNX).

## Learned Workspace Facts

- **`py/` and `assets/` belong at the install/repo root**, not under `.cursor/` — `.cursor/` is the Cursor adapter (hooks, commands, rules, local state); the Python runtime and ONNX weights are shared across adapters.
- Canonical first-time install: `curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash -s -- --install-uv --start-daemon` (global hooks + `~/aftertone` by default).
