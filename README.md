# Aftertone

<p align="center">
  <img src="img/aftertone-logo.png" alt="Aftertone — local text-to-speech for AI coding agents and Cursor hooks" width="480">
</p>

**Hear a short spoken line after your coding agent answers** — on-device **[Supertonic](https://github.com/supertone-inc/supertonic) ONNX** through a tiny **local HTTP daemon** (models stay loaded; hooks stay fast).

Aftertone is **not Cursor-only**. Today it ships a **Cursor** `afterAgentResponse` integration; we want first-class paths for **Claude Code / Claude Desktop** and **OpenAI Codex** (CLI or IDE). If that excites you, read [CONTRIBUTING.md](CONTRIBUTING.md) and open a PR or design issue.

## Discovery

If you are searching for **local text-to-speech**, **on-device** assistants, **AI coding agent** tooling, **agentic coding** workflows, or **Cursor IDE** **hooks** that do not send your thread to a cloud API — Aftertone is a small **open source** **developer tool**: **ONNX Runtime** + **Supertonic** for optional **voice** feedback after the model answers, **offline**-friendly and **privacy**-minded.

**Related GitHub topics:** [ai-agents](https://github.com/topics/ai-agents) · [coding-agent](https://github.com/topics/coding-agent) · [cursor](https://github.com/topics/cursor) · [text-to-speech](https://github.com/topics/text-to-speech) · [onnx](https://github.com/topics/onnx) · [local-first](https://github.com/topics/local-first) · [developer-tools](https://github.com/topics/developer-tools) · [open-source](https://github.com/topics/open-source)

## Features (today)

- **Cursor:** `afterAgentResponse` → optional TTS from inline reply text (prefers `<spoken_summary>…</spoken_summary>`).
- `speak_summary_prepare.py` → JSON for `POST /say`; `tts_daemon.py` → localhost server.
- Optional `stop` hook trace for debugging.
- `bash scripts/bootstrap.sh` — `uv sync`, Hugging Face assets if `assets/onnx/` is missing.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Cursor (current adapter):** Hooks on, **trusted** workspace, `.cursor/hooks.json` with `"version": 1`.
- ONNX weights under `./assets` (`Supertone/supertonic-3` — bootstrap downloads them).

## Quick start

```bash
git clone https://github.com/omarelkhal/aftertone.git
cd aftertone
bash scripts/bootstrap.sh
```

**Cursor:** open this folder as the workspace root so project hooks load.

- **Daemon:** `cd py && uv run python tts_daemon_ctl.py status --repo-root ..`
- **Smoke (needs assets + audio):** `bash py/test_speak_summary_pipeline.sh`
- **Diagnostics:** `bash py/diagnose_speak_hooks.sh`

### Repo root env (any adapter)

Hooks and Python resolve the install root via **`AFTERTONE_REPO`** (preferred) or legacy **`SUPERTONIC_REPO`**.

### Copy into another repo

Bring `.cursor/` + `py/` (or symlink). Keep `speak_summary.toml` paths consistent (`../assets/onnx`, etc.).

## Configuration

| Doc / file | Role |
|------------|------|
| **[`.cursor/hooks/README.md`](.cursor/hooks/README.md)** | **Full reference:** every `speak_summary.toml` key, `lang` list, heuristics, `quiet_hours`, daemon **start/stop/status/restart**, logs. |
| [`.cursor/hooks/speak_summary.toml`](.cursor/hooks/speak_summary.toml) | Port, voice, `lang`, speed, GPU, quiet hours, limits, heuristics. |
| [`.cursor/rules/spoken-summary.mdc`](.cursor/rules/spoken-summary.mdc) | When/how to emit `<spoken_summary>`; **match TOML `lang`** inside the tag; write for speech. |

Disable speech: `enabled = false` in `speak_summary.toml`.

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** and the **[Code of Conduct](CODE_OF_CONDUCT.md)**. **Issues:** [open one here](https://github.com/omarelkhal/aftertone/issues) — use a template (**Bug report**, **Feature or idea**, **Adapter research**). Starter ideas: [.github/STARTER_ISSUES.md](.github/STARTER_ISSUES.md).

## Website

**[aftertone on GitHub Pages](https://omarelkhal.github.io/aftertone/)** — static landing built from the [`docs/`](docs/) folder. Enable in the **repository** (not your profile): **aftertone → Settings → Pages** → source **Deploy from a branch**, branch **`main`**, folder **`/docs`**. (Profile **Settings → Pages** only shows *verified domains* — that’s a different screen.)

## License

MIT — [LICENSE](LICENSE). Supertonic-derived code: [NOTICE](NOTICE).

## Publish to GitHub

```bash
cd /path/to/aftertone
git remote add origin https://github.com/omarelkhal/aftertone.git
git push -u origin main
```

Or: `gh repo create aftertone --public --source=. --remote=origin --push`
