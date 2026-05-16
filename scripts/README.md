# `scripts/`

- **`install.sh`** — one-line install (clone or update, then bootstrap). See [README](../README.md#one-line-install).
- **`bootstrap.sh`** — from repo root: `uv sync` in `py/`, download `Supertone/supertonic-3` into `assets/` when ONNX files are missing, optional `npm install` in `web/` if that directory exists.

## `install.sh` options

| Flag | Meaning |
|------|---------|
| `--dir PATH` | Clone location (default `~/aftertone`) |
| `--into PATH` | Copy `.cursor` hooks/commands/rules + `py/` into another repo; symlink `assets/` |
| `--branch NAME` | Git branch (default `main`) |
| `--skip-assets` | Skip model download |
| `--start-daemon` | Run `tts_daemon_ctl.py start` after bootstrap |
| `--install-uv` | Install [uv](https://docs.astral.sh/uv/) via Astral script if missing |

Env: `AFTERTONE_INSTALL_DIR`, `AFTERTONE_REPO_URL`, `AFTERTONE_BRANCH`.

`bootstrap.sh` env: `SKIP_ASSETS=1`, `SKIP_WEB=1`, `FORCE_ASSETS=1`.
