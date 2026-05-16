# Aftertone — Cursor spoken TTS: hooks, daemon, and `speak_summary.toml`

This folder holds the **Cursor hook** scripts, **`hooks.json`**, and **`speak_summary.toml`** (single source of config for the hook + daemon control). State (PID, port, logs, spoken JSONL) lives in [`state/`](state/).

---

## Toggle spoken TTS from Cursor (no daemon restart)

`enabled` in `speak_summary.toml` is read on **every** agent reply. Flip it without editing the file by hand:

```bash
cd py && uv run python speak_summary_toggle.py toggle   # or: on | off | status
```

**In the IDE:** **Terminal → Run Task…** → **Aftertone: toggle spoken TTS** (see [`.vscode/tasks.json`](../../.vscode/tasks.json)). Bind a shortcut under **Keyboard Shortcuts** → search `Tasks: Run Task` or assign a key to that task name.

Cursor does not ship a dedicated Aftertone status-bar widget; this task + optional keybinding is the lightweight equivalent. Turning TTS off does not stop the daemon; use `tts_daemon_ctl.py stop` if you want silence and no loaded models.

---

## Daemon: start, stop, status, restart

Run from **`py/`** with repo root one level up (adjust if your clone path differs):

```bash
cd py
uv sync
uv run python tts_daemon_ctl.py start --repo-root ..
uv run python tts_daemon_ctl.py status --repo-root ..
uv run python tts_daemon_ctl.py stop --repo-root ..
uv run python tts_daemon_ctl.py restart --repo-root ..
```

| Command | What it does |
|--------|----------------|
| **`start`** | Reads `speak_summary.toml`, spawns `tts_daemon.py` in the background, writes `state/tts-daemon.pid` and `state/tts-daemon.port`, waits for `/healthz`. |
| **`stop`** | Sends SIGTERM to the PID in `state/tts-daemon.pid`, removes the PID file. |
| **`status`** | Prints **current TOML on disk** (voice path, port, lang, speed, `use_gpu`), then whether the process is alive and **`GET /healthz`** output (includes the voice file path the daemon was started with). |
| **`restart`** | `stop` then `start`. **Use this after changing any TOML field that only applies at daemon startup** (see table below). |

**Optional:** `uv run python tts_daemon_ctl.py start --repo-root .. --port 9999` overrides the TOML `port` for that start only.

**Environment:** `SUPERTONIC_REPO` — absolute path to the repo root; set automatically by `speak_summary.sh` when the hook runs.

---

## When TOML changes apply (restart or not)

| Keys | When they apply | Need `restart`? |
|------|------------------|-----------------|
| **`enabled`**, **`quiet_hours`**, **`min_chars`**, **`max_chars`**, **`spoken_summary_max_chars`**, **`heuristic_max_chars`**, **`plain_excerpt_max_chars`**, **`heuristic_max_sentences`**, **`heuristic_code_fence_fraction`**, **`heuristic_max_sentences_code_heavy`**, **`only_speak_spoken_summary`** | Read **every** hook run by `speak_summary_prepare.py` — they control **whether** to speak and **which text** is chosen (not sent as separate fields on `/say`). | **No** |
| **`speed`**, **`lang`**, **`total_step`**, **`mode`** | Read every hook run; included in the **`POST /say`** JSON body. | **No** |
| **`port`**, **`onnx_dir`**, **`voice_style`**, **`voice_type`**, **`use_gpu`** | Read only when **`tts_daemon`** **starts** (`tts_daemon_ctl.py start`). Models and voice JSON load once. | **Yes** — `restart` (or `stop` then `start`). |

**Port file caveat:** While the daemon is running, `speak_summary.sh` prefers **`state/tts-daemon.port`** over re-parsing TOML for the **HTTP port**. If you change `port` in TOML but do not restart, the hook still posts to the **old** port until `restart` updates the file. A **`port_mismatch`** line is written to `state/speak_summary-hook.log` when TOML `port` ≠ port file.

---

## Full reference: `speak_summary.toml`

Paths like `../assets/...` are **relative to `py/`** (because the daemon is started with `cwd=py/`).

### `enabled`

- **Meaning:** Master switch for the **prepare** step (no JSON payload → hook does not `POST /say`).
- **Type:** Boolean TOML `true` / `false`, or treated as off if string is one of: `0`, `false`, `no`, `off` (case-insensitive).
- **Restart?** No.

### `port`

- **Meaning:** TCP port for **`tts_daemon`** HTTP server (`127.0.0.1:<port>/healthz`, `/say`, `/shutdown`).
- **Type:** Integer. Typical: `8765` or any free high port.
- **Restart?** **Yes**, after changing.
- **Note:** Hook reads **`state/tts-daemon.port`** when present; restart aligns file + TOML.

### `onnx_dir`

- **Meaning:** Directory with Supertonic ONNX models (same as CLI `--onnx-dir`).
- **Type:** String path, default `../assets/onnx` from `py/`.
- **Restart?** **Yes**.

### `use_gpu`

- **Meaning:** Passed to daemon startup; requests GPU execution providers when `onnxruntime-gpu` + CUDA are available (see `py/helper.py`).
- **Type:** Boolean `true` / `false`.
- **Restart?** **Yes**.

### `mode`

- **Meaning:** Queuing behavior for overlapping `/say` requests, sent on each `POST /say`.
- **Type:** String, case-insensitive.
- **Allowed values:** **`queue`** (default) — wait for previous playback; **`interrupt`** — stop current playback, drain queue, speak the new line immediately.
- **Restart?** No (read each hook).

### `voice_type`

- **Meaning:** Short preset id for the voice JSON under `assets/voice_styles/`. Used **only when** `voice_style` is empty or whitespace.
- **Type:** String, e.g. `M1`, `F2`. If the value does not end with `.json`, **`.json` is appended** and resolved as `../assets/voice_styles/<name>.json` from `py/`.
- **Restart?** **Yes** (voice loaded at daemon start).
- **Discover presets:** After assets are installed:  
  `ls "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/assets/voice_styles"/*.json`  
  (or check the Hugging Face bundle `Supertone/supertonic-3`.)

### `voice_style`

- **Meaning:** Explicit path to one **voice style JSON** file (same as `--voice-style`).
- **Type:** String. Relative to **`py/`** or absolute. Non-empty value **wins over** `voice_type`.
- **Example:** `../assets/voice_styles/M1.json`
- **Restart?** **Yes**.

### `lang`

- **Meaning:** The **natural language of the words** you want TTS to speak **and** the ONNX text-processor code (the model wraps your string as `<lang>…</lang>`). Sent on every **`POST /say`**.
- **Type:** String; must be one of the codes below or synthesis raises **`Invalid language`**.
- **Restart?** No.
- **No auto-translation:** `speak_summary_prepare.py` does **not** translate the assistant reply. Whatever string is chosen (tag or heuristic) is sent as-is. If the reply is English but `lang` is `fr`, you should put French inside `<spoken_summary>…</spoken_summary>`, or set **`only_speak_spoken_summary = true`** so heuristics never pull English. Agents: see [`.cursor/rules/spoken-summary.mdc`](../rules/spoken-summary.mdc).
- **Heuristic fallback:** When there is **no** tag, the hook reuses **snippets of the assistant message** (often English). That only matches `lang` if the message is already in that language — otherwise use the tag or enable **`only_speak_spoken_summary`**.
- **Rule file stays in sync:** [`.cursor/rules/spoken-summary.mdc`](../rules/spoken-summary.mdc) contains an **auto-generated** line with the current TOML `lang`. After you change `lang`, run from **repo root**: `uv run --directory py python sync_spoken_rule_lang.py` (optional `--check` for CI). See [`py/sync_spoken_rule_lang.py`](../../py/sync_spoken_rule_lang.py).

**Allowed `lang` values** (from `py/helper.py` `AVAILABLE_LANGS`, 31 codes):

`ar`, `bg`, `cs`, `da`, `de`, `el`, `en`, `es`, `et`, `fi`, `fr`, `hi`, `hr`, `hu`, `id`, `it`, `ja`, `ko`, `lt`, `lv`, `nl`, `pl`, `pt`, `ro`, `ru`, `sk`, `sl`, `sv`, `tr`, `uk`, `vi`

### `speed`

- **Meaning:** Speech rate factor passed into inference (higher = faster utterance; same semantics as `py/example_onnx.py` `--speed`).
- **Type:** Float. Default in examples is often **`1.05`**.
- **Practical range:** `py/README.md` recommends roughly **`0.9`–`1.5`** for natural sound; very low or very high may sound odd but are not hard-rejected by the hook.
- **Restart?** No.

### `total_step`

- **Meaning:** ONNX denoising steps (quality vs CPU time). Same idea as `--total-step` in examples (defaults differ: daemon TOML often `4`, `example_onnx` default `8`).
- **Type:** Integer ≥ `1` (passed as `totalStep` on `/say`; invalid values may fail at runtime).
- **Restart?** No.

### `quiet_hours`

- **Meaning:** If the **local** clock falls inside this window, the prepare script prints `{}` and nothing is spoken.
- **Type:** String.
- **Disabled:** empty string `""`, or `none` / `off` / `false` (case-insensitive).
- **Same-day window:** `"09:00-17:00"` — quiet from 09:00 inclusive to 17:00 **exclusive** (24h `HH:MM`, hours 0–23).
- **Overnight window:** `"22:00-08:00"` — quiet from 22:00 **or** before 08:00.
- **Bypass for testing:** environment variable **`SPEAK_SUMMARY_IGNORE_QUIET=1`** (values `1`, `true`, `yes`).
- **Restart?** No.

### `min_chars`

- **Meaning:** Minimum length of the **chosen** speakable string (after tag extraction / heuristics). Shorter → prepare outputs `{}` (no TTS).
- **Type:** Integer, default **`5`** in code if omitted.
- **Example:** `min_chars = 5` avoids one-letter noise; raise if you want longer minimum blurbs.
- **Restart?** No.

### `max_chars`

- **Meaning:** Upper bound for **heuristic** and **plain-excerpt** paths, and for `<spoken_summary>` **only when** `spoken_summary_max_chars` is **`0`** (see below).
- **Type:** Integer. **`0` or negative** means **no limit** on those paths (very long replies → very long audio).
- **Restart?** No.

### `spoken_summary_max_chars`

- **Meaning:** Maximum characters taken from **inside** `<spoken_summary>…</spoken_summary>` after markdown stripping and **leading-sentence** assembly (the hook does not read the whole tag if it is a wall of text). Prevents the annoyance where TTS reads an entire assistant essay because it was wrapped in the tag or the tag was huge.
- **Type:** Integer. Default **`360`** in code if the key is omitted. **`0`** means “use **`max_chars`** for the tag too” (legacy behavior).
- **Restart?** No.

### `heuristic_max_chars`

- **Meaning:** Hard cap for the **no-tag** sentence heuristic (default **`480`**). Independent of `max_chars` so raising `max_chars` for other reasons does not let one giant “sentence” (few `.!?` breaks) run for minutes.
- **Type:** Integer. **`0`** = use **`max_chars`** only.
- **Restart?** No.

### `plain_excerpt_max_chars`

- **Meaning:** Cap for the last-resort **plain excerpt** path when heuristics are still too short (default **`420`**).
- **Type:** Integer. **`0`** = use **`max_chars`** only.
- **Restart?** No.

### `heuristic_max_sentences`

- **Meaning:** When there is **no** `<spoken_summary>` tag, the fallback splitter may join up to this many **sentences** after skipping “soft opener” lines (e.g. “Sure,” “Here’s…”).
- **Type:** Integer, **clamped to `1`–`3`** in code.
- **Examples:** `1` — one short line; `2` — often “what + a bit of why”; `3` — rarer, longer earful.
- **Restart?** No.

### `heuristic_code_fence_fraction`

- **Meaning:** If the fraction of **raw assistant text characters** inside **markdown fenced code blocks** (regions between triple-backtick fences) is **≥ this value**, the reply is treated as **code-heavy** and the fallback uses **`heuristic_max_sentences_code_heavy`** instead of `heuristic_max_sentences`.
- **Type:** Float, **clamped to `0.05`–`0.95`** in code. Default **`0.35`**.
- **Example:** `0.5` — only very code-dense messages get the shorter cap.
- **Restart?** No.

### `heuristic_max_sentences_code_heavy`

- **Meaning:** Max fallback sentences when **code-heavy** (see above).
- **Type:** Integer, **clamped `1`–`3`**. Default **`1`**.
- **Restart?** No.

### `only_speak_spoken_summary`

- **Meaning:** If **`true`**, the prepare script outputs **`{}`** whenever the assistant message has **no** `<spoken_summary>…</spoken_summary>` block — no sentence heuristics and no plain excerpt. Guarantees TTS never reads a language mismatch from fallbacks; you must write the tag in the same language as **`lang`**.
- **Type:** Boolean. Default **`false`** (backward compatible: heuristics still run without a tag).
- **Restart?** No.

---

## Hook files (quick map)

| File | Role |
|------|------|
| [`hooks.json`](hooks.json) | Cursor hook registration (`version: 1`, `afterAgentResponse` → `speak_summary.sh`). |
| [`speak_summary.toml`](speak_summary.toml) | Config for prepare + daemon control (this doc). |
| [`speak_summary.sh`](speak_summary.sh) | Shell: stdin JSON → `speak_summary_prepare.py` → `curl POST /say`, bootstraps daemon if needed. |
| [`hook_payload_trace.sh`](hook_payload_trace.sh) | Optional tracing for `stop` / debugging. |

---

## Logs and verification

- **Hook log:** `state/speak_summary-hook.log`
- **Prepare stderr:** `state/speak_summary-prepare.stderr.log`
- **Daemon log:** `state/tts-daemon.log`
- **Spoken lines:** `state/spoken/YYYY-MM-DD.jsonl`
- **Smoke test:** from repo: `bash py/test_speak_summary_pipeline.sh` → must end with `OK:`

After a real Cursor reply: `bash py/diagnose_speak_hooks.sh` and check `state/hook_payload_trace.jsonl` for `afterAgentResponse` with `inline_after_response_ok: true`.

---

## Agent-authored speech (optional)

Models can end replies with:

```text
<spoken_summary>
Plain words only, no markdown, no URLs.
</spoken_summary>
```

See [`.cursor/rules/spoken-summary.mdc`](../rules/spoken-summary.mdc) for writing rules. The hook **prefers** this block over heuristics.

---

## More context in the repo

- [AGENTS.md](../../AGENTS.md) — Cursor TTS overview and “TOML does nothing” troubleshooting.
- [py/README.md](../../py/README.md) — ONNX CLI args, speed guidance, daemon bullets.
- [py/speak_summary_prepare.py](../../py/speak_summary_prepare.py) — exact parsing and clamps.
- [py/tts_daemon_ctl.py](../../py/tts_daemon_ctl.py) — start/stop and TOML → daemon argv.
