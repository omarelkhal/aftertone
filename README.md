# Aftertone

**Hear a short spoken line after your coding agent answers** — on-device **[Supertonic](https://github.com/supertone-inc/supertonic) ONNX** through a tiny **local HTTP daemon** (models stay loaded; hooks stay fast).

Aftertone is **not Cursor-only**. Today it ships a **Cursor** `afterAgentResponse` integration; we want first-class paths for **Claude Code / Claude Desktop** and **OpenAI Codex** (CLI or IDE). If that excites you, read [CONTRIBUTING.md](CONTRIBUTING.md) and open a PR or design issue.

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
git clone https://github.com/YOUR_USER/aftertone.git
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

| File | Role |
|------|------|
| `.cursor/hooks/speak_summary.toml` | Port, `quiet_hours`, `min_chars` / `max_chars`, GPU |
| `.cursor/rules/spoken-summary.mdc` | Model text: when/how to emit `<spoken_summary>` |

Disable speech: `enabled = false` in `speak_summary.toml`.

## License

MIT — [LICENSE](LICENSE). Supertonic-derived code: [NOTICE](NOTICE).

## Publish to GitHub

```bash
cd /path/to/aftertone
git remote add origin https://github.com/YOUR_USER/aftertone.git
git push -u origin main
```

Or: `gh repo create aftertone --public --source=. --remote=origin --push`
