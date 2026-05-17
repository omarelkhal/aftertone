# Aftertone

<p align="center">
  <img src="img/aftertone-logo.png" alt="Aftertone — local text-to-speech for AI coding agents and Cursor hooks" width="480">
</p>

**Hear a short spoken line after your coding agent answers** — on-device **[Supertonic](https://github.com/supertone-inc/supertonic) ONNX** through a tiny **local HTTP daemon** (models stay loaded; hooks stay fast).

One daemon, thin adapters per tool — **Cursor ships today**; **Claude Code**, **Codex**, and **OpenCode** are on the roadmap. Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md) and the **Adapter research** issue template.

☕ **[Support development](https://buymeacoffee.com/elkhalomar)** on Buy Me a Coffee — helps maintain Aftertone and new agent adapters.

## Works with

<p align="center">
  <strong>AI coding agents &amp; IDEs</strong><br>
  <sub>Same local <code>tts_daemon</code> — each adapter wires “reply finished” → short spoken line</sub>
</p>

<div align="center">
  <table>
    <tr>
      <td align="center" width="140">
        <a href="https://cursor.com" title="Cursor"><img src="https://cdn.simpleicons.org/cursor/1a1714" alt="Cursor" height="44" /></a><br>
        <strong>Cursor</strong><br>
        <sub>✅ Available</sub>
      </td>
      <td align="center" width="140">
        <a href="https://docs.anthropic.com/en/docs/claude-code" title="Claude Code"><img src="img/adapters/claude.svg" alt="Claude Code" height="44" style="opacity:0.55" /></a><br>
        <strong>Claude Code</strong><br>
        <sub>Coming soon</sub>
      </td>
      <td align="center" width="140">
        <a href="https://developers.openai.com/codex" title="OpenAI Codex"><img src="img/adapters/codex.svg" alt="Codex" height="44" style="opacity:0.55" /></a><br>
        <strong>Codex</strong><br>
        <sub>Coming soon</sub>
      </td>
      <td align="center" width="140">
        <a href="https://opencode.ai" title="OpenCode"><img src="img/adapters/opencode.svg" alt="OpenCode" height="44" style="opacity:0.55" /></a><br>
        <strong>OpenCode</strong><br>
        <sub>Coming soon</sub>
      </td>
    </tr>
  </table>
</div>

<p align="center">
  <sub>Missing your stack? Open an <a href="https://github.com/omarelkhal/aftertone/issues/new?template=adapter_research.md">adapter research</a> issue — tracked in <a href="CONTRIBUTING.md#what-were-building">CONTRIBUTING</a>.</sub>
</p>

## Discovery

If you are searching for **local text-to-speech**, **on-device** assistants, **AI coding agent** tooling, **agentic coding** workflows, or **Cursor IDE** **hooks** that do not send your thread to a cloud API — Aftertone is a small **open source** **developer tool**: **ONNX Runtime** + **Supertonic** for optional **voice** feedback after the model answers, **offline**-friendly and **privacy**-minded.

**Related GitHub topics:** [ai-agents](https://github.com/topics/ai-agents) · [coding-agent](https://github.com/topics/coding-agent) · [cursor](https://github.com/topics/cursor) · [text-to-speech](https://github.com/topics/text-to-speech) · [onnx](https://github.com/topics/onnx) · [local-first](https://github.com/topics/local-first) · [developer-tools](https://github.com/topics/developer-tools) · [open-source](https://github.com/topics/open-source)

## Features (today)

- **Cursor:** `afterAgentResponse` → optional TTS from inline reply text (prefers the **last** `<spoken_summary>…</spoken_summary>` at the end of the reply).
- **Flow briefings:** agents write a short listening line (state, why it matters, optional next move) — see [spoken-summary rule](.cursor/rules/spoken-summary.mdc). Repo default: **`only_speak_spoken_summary = true`** (no heuristic fallback).
- **Livelier delivery:** end each sentence in the tag with `!!`, `??`, `?!`, or `!?` (Supertonic prosody); **`expression_mode = "off"`** by default (inline `<sigh>` tags are optional via `/aftertone-expression`).
- **Slash commands** in Agent chat (`/aftertone-lang`, `/aftertone-voice`, `/aftertone-restart`, …) — no hand-editing TOML for everyday changes.
- `speak_summary_prepare.py` → JSON for `POST /say`; `tts_daemon.py` → localhost server.
- Optional `stop` hook trace for debugging.
- `bash scripts/bootstrap.sh` — `uv sync`, Hugging Face assets if `assets/onnx/` is missing.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Cursor (current adapter):** Hooks on, **trusted** workspace, `.cursor/hooks.json` with `"version": 1`.
- ONNX weights under `./assets` (`Supertone/supertonic-3` — bootstrap downloads them).

## Quick start

### One-line install

Requires **git**. Installs **once** to **`~/aftertone`** (clone + `uv sync` + model download) and registers **user-level Cursor hooks** so spoken TTS works in **every project** you open — no per-repo copy.

```bash
curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash -s -- --install-uv --start-daemon
```

Options (pass after `bash -s --`):

```bash
curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash -s -- --dir ~/code/aftertone
curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash -s -- --no-global   # skip ~/.cursor hooks
```

**Legacy:** copy hooks + `py/` into one repo (`--into .`) — only if you cannot use global hooks.

See [`scripts/install.sh`](scripts/install.sh) and [`scripts/README.md`](scripts/README.md).

### Manual clone

```bash
git clone https://github.com/omarelkhal/aftertone.git
cd aftertone
bash scripts/bootstrap.sh
```

**Cursor:** enable **Hooks** in Settings and **trust** each workspace where you want TTS. After a global install, hooks live in **`~/.cursor/hooks.json`** (not in every project). Slash commands are copied to **`~/.cursor/commands/`**; config still reads **`~/aftertone/.cursor/hooks/speak_summary.toml`**.

- **Daemon:** `cd py && uv run python tts_daemon_ctl.py start --repo-root ..` then `status`
- **Smoke (needs assets + audio):** `bash py/test_speak_summary_pipeline.sh`
- **Diagnostics:** `bash py/diagnose_speak_hooks.sh`

### Repo root env (any adapter)

Hooks and Python resolve the install root via **`AFTERTONE_REPO`** (preferred) or legacy **`SUPERTONIC_REPO`**.

### Global install layout

| Path | Purpose |
|------|---------|
| `~/aftertone/` | One clone: `py/`, `assets/`, config TOML, daemon |
| `~/.cursor/hooks.json` | User hooks → `aftertone-speak_summary.sh` |
| `~/.cursor/hooks/aftertone-install-dir` | Points at `~/aftertone` |
| `~/.cursor/commands/aftertone-*.md` | Slash commands (any workspace) |

### Copy into another repo (legacy)

`install.sh --no-global --into .` duplicates hooks + `py/` in that repo. Prefer the global install above.

## Control (Cursor slash commands)

In **Agent** chat, type **`/`** and pick an **`aftertone-`** command (available in any workspace after global install). That is the **supported** way to change spoken-TTS settings — do **not** hand-edit [`.cursor/hooks/speak_summary.toml`](.cursor/hooks/speak_summary.toml) for everyday changes.

| Command | What it does | Daemon restart? |
|---------|----------------|-----------------|
| `/aftertone-toggle` | Flip spoken TTS on/off | No |
| `/aftertone-on` / `/aftertone-off` | Force on or off | No |
| `/aftertone-status` | Current settings + daemon health | No |
| `/aftertone-lang` | Pick language (syncs [spoken-summary rule](.cursor/rules/spoken-summary.mdc)) | No |
| `/aftertone-speed` | Pick playback speed | No |
| `/aftertone-mode` | Pick `queue` or `interrupt` | No |
| `/aftertone-expression` | Supertonic inline expression tags (`off` / `subtle` / …); repo default **`off`** | No |
| `/aftertone-voice` | Pick a voice (e.g. Sara (female), James (male)) | **Yes** (command restarts for you) |
| `/aftertone-restart` | Reload daemon after **port**, **voice**, **onnx_dir**, or **use_gpu** changes | **Yes** |

Command definitions: [`.cursor/commands/`](.cursor/commands/).

**Daemon CLI (advanced):** `cd py && uv run python tts_daemon_ctl.py {start|stop|status|restart} --repo-root ..` — see [`.cursor/hooks/README.md`](.cursor/hooks/README.md). Prefer **`/aftertone-restart`** in Agent chat when voice or port changed. Turning TTS **off** via `/aftertone-off` does not unload models; use **stop** when you want silence and no GPU/RAM use.

### Spoken summaries (agents)

Put **one** `<spoken_summary>…</spoken_summary>` block at the **very end** of substantive replies (plain language, same language as TOML `lang`). The hook pairs the **last** closing tag with the nearest opening tag before it — so do not leave an unclosed `<spoken_summary>` mention in code or prose above your real tag.

For **vibe coding**, write a hybrid pair-programmer briefing: what happened, why it matters, optional next move. For livelier TTS, end **each sentence** in the tag with `!!`, `??`, `?!`, or `!?`. Full guidance: [`.cursor/rules/spoken-summary.mdc`](.cursor/rules/spoken-summary.mdc).

## Configuration

| Doc / file | Role |
|------------|------|
| **[`.cursor/hooks/README.md`](.cursor/hooks/README.md)** | **Full TOML reference:** every `speak_summary.toml` key, valid `lang` codes, heuristics, `quiet_hours`, daemon **start / stop / status / restart**, logs, when changes need a restart. |
| [`.cursor/hooks/speak_summary.toml`](.cursor/hooks/speak_summary.toml) | On-disk config (updated by slash commands and install). |
| [`.cursor/rules/spoken-summary.mdc`](.cursor/rules/spoken-summary.mdc) | When/how agents emit `<spoken_summary>`; **match TOML `lang`**. |
| **[`AGENTS.md`](AGENTS.md)** | Agent-oriented digest (flow, verify hooks, caps, “nothing speaks”). |

## Support

If Aftertone saves you from reading every agent wall of text, consider **[buying me a coffee](https://buymeacoffee.com/elkhalomar)**. Tips fund maintenance, docs, and adapters (Claude Code, Codex, OpenCode). Code contributions are always welcome too — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** and the **[Code of Conduct](CODE_OF_CONDUCT.md)**. **Issues:** [open one here](https://github.com/omarelkhal/aftertone/issues) — use a template (**Bug report**, **Feature or idea**, **Adapter research**). Starter ideas: [.github/STARTER_ISSUES.md](.github/STARTER_ISSUES.md).

## Website

**[aftertone on GitHub Pages](https://omarelkhal.github.io/aftertone/)** — home + **[docs](https://omarelkhal.github.io/aftertone/docs.html)** (one-line install, slash commands, daemon, troubleshooting). Built from [`docs/`](docs/).

## License

MIT — [LICENSE](LICENSE). Supertonic-derived code: [NOTICE](NOTICE).
