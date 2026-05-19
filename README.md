# Aftertone

<p align="center">
  <img src="img/aftertone-logo.png" alt="Aftertone — local text-to-speech for AI coding agents" width="420">
</p>

<p align="center">
  <strong>Local speech after each agent reply</strong> — Supertonic ONNX on your machine, no cloud TTS API.<br>
  Free (MIT). Install once. Works across projects.
</p>

<p align="center">
  <a href="https://buymeacoffee.com/elkhalomar"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy me a coffee" width="217" height="60" /></a>
</p>

<p align="center"><sub>Demo — Claude Code with <code>/aftertone_on</code> (short question + clone-a-repo). Unmute for audio.</sub></p>

https://github.com/omarelkhal/aftertone/blob/main/docs/demo.mp4?raw=1

<p align="center"><sub>Hear the spoken summary when each reply finishes — not the full reply on screen.</sub></p>

## Adapters

| | Cursor | Claude Code | Codex | OpenCode |
|---|:---:|:---:|:---:|:---:|
| Status | ✅ | ✅ | soon | soon |

Same `tts_daemon` for all — each adapter runs a hook when a reply finishes. [Claude setup](docs/adapters/claude.md) · [Contributing](CONTRIBUTING.md)

## Install

**Linux / macOS** (needs git + bash):

```bash
curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash -s -- --install-uv --start-daemon
```

**Windows** (PowerShell, needs [Git for Windows](https://git-scm.com/download/win)):

```powershell
irm https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.ps1 | iex
```

Installs to `~/aftertone` (or `%USERPROFILE%\aftertone`), downloads models, registers hooks, starts the daemon, enables TTS.

**Then:**

| Tool | You do |
|------|--------|
| **Cursor** | Settings → **Hooks** on · **trust** the workspace |
| **Claude Code** | `claude` → `/aftertone_on` in each chat where you want speech |

Agents should end substantive replies with `<spoken_summary>…</spoken_summary>` (repo default: **tag only** — no tag, no speech). See [spoken-summary rule](.cursor/rules/spoken-summary.mdc).

More options, uninstall, manual clone: **[docs](https://omarelkhal.github.io/aftertone/docs.html)** · [`scripts/`](scripts/)

## Control

Type `/` in Agent chat. **Do not** hand-edit TOML for everyday changes.

### Per-session on/off

**`/aftertone-on`** and **`/aftertone-off`** (Claude: `/aftertone_on` / `/aftertone_off`) apply to **this chat only**. Run **`/aftertone-on`** in each Composer or Claude session where you want speech; other sessions stay silent until you enable them there too. After **`/aftertone-on`**, send any agent reply so the hook can register that session.

| Cursor | Claude Code |
|--------|-------------|
| `/aftertone-on` `/aftertone-off` `/aftertone-toggle` | `/aftertone_on` `/aftertone_off` `/aftertone_toggle` |
| `/aftertone-status` | `/aftertone_status` |
| `/aftertone-lang` `/aftertone-voice` `/aftertone-restart` | `/aftertone_lang` `/aftertone_voice` `/aftertone_restart` |
| … [docs](https://omarelkhal.github.io/aftertone/docs.html#slash-commands) | … [Claude guide](docs/adapters/claude.md) |

Power-user: `aftertone session list`, `aftertone session clear`, `aftertone global-off` (mute everywhere).

**CLI** (same as slash commands):

```bash
cd "$(cat ~/.cursor/hooks/aftertone-install-dir)"
uv run --directory py python -m aftertone status
```

## Troubleshooting

- **`/aftertone-doctor`** or `uv run --directory py python -m aftertone doctor`
- Logs: `<install>/.cursor/hooks/state/speak_summary-hook.log`
- **Windows:** Cursor may delay hooks for seconds before Aftertone runs — [details](https://omarelkhal.github.io/aftertone/docs.html#windows-hook-latency)

Config reference: [`.cursor/hooks/README.md`](.cursor/hooks/README.md) · Agent notes: [`AGENTS.md`](AGENTS.md)

## Links

- **Site:** [omarelkhal.github.io/aftertone](https://omarelkhal.github.io/aftertone/)
- **Issues:** [github.com/omarelkhal/aftertone/issues](https://github.com/omarelkhal/aftertone/issues)
- **License:** [MIT](LICENSE) (code) · Supertonic weights: [NOTICE](NOTICE)
