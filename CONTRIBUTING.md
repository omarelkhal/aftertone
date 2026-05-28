# Contributing to Aftertone

Thanks for helping make **local, private “hear the gist”** work across more than one tool.

## Community

- This project follows the **[Code of Conduct](CODE_OF_CONDUCT.md)**. By participating, you agree to uphold it.
- **Issues:** use [GitHub Issues](https://github.com/omarelkhal/aftertone/issues) and pick a template (**Bug report**, **Feature or idea**, **Adapter research**) so we can triage quickly.

## What we’re building

| Area | Status | Help wanted |
|------|--------|-------------|
| **Cursor** `afterAgentResponse` + `tts_daemon` | Shipped | Bugfixes, docs, Windows audio edge cases |
| **Claude Code** (`Stop` hook + slash commands) | Shipped — [docs/adapters/claude.md](docs/adapters/claude.md) | [Contributor todos — Claude](#claude-code-contributor-todos) |
| **OpenAI Codex** (`Stop` hook + guidance) | Shipped — [docs/adapters/codex.md](docs/adapters/codex.md) | Optional MCP control and edge-case docs |
| **OpenCode**, **GitHub Copilot**, **Windsurf**, **JetBrains AI**, **Zed**, **Cline**, **Continue** | Not shipped | Same pattern: final assistant text → `speak_summary_prepare.py` or `POST /say` |
| **Core** daemon + ONNX pipeline | Shipped | Performance, GPU docs, packaging |

Optional **MCP control plane** (on/off, status, `set`, restart) lives in `py/aftertone/mcp_server.py` and [`scripts/cursor-global/mcp.aftertone.json`](scripts/cursor-global/mcp.aftertone.json). It delegates to `python -m aftertone` — **not** the post-reply speech trigger. Cursor uses **slash commands** for control; Claude/Codex adapters should reuse the same CLI and optionally expose MCP where the host supports it.

## Claude Code — contributor todos

Speech (required for “Aftertone works here”):

- [x] **Research** — `Stop` + `transcript_path`; see [`docs/adapters/claude.md`](docs/adapters/claude.md).
- [x] **Payload** — `Stop` accepted in `prepare.py`; plugin delegates to `speak_summary.sh` → `hook_run` / `/say`.
- [x] **Install path** — Global install (`install.sh` → `py/install_global_claude_hooks.py`, default `~/aftertone`); optional [`claude-plugin/aftertone/`](claude-plugin/aftertone/) for `--plugin-dir`.
- [x] **Config** — Shared `speak_summary.toml` under install `.cursor/hooks/` (documented in [`docs/adapters/claude.md`](docs/adapters/claude.md)).
- [x] **Model guidance** — `~/.claude/rules/spoken-summary.md` on install; mirrors Cursor spoken-summary rule (`lang` + `<spoken_summary>`).
- [x] **Smoke test** — `bash py/test_speak_summary_pipeline.sh` + Claude steps in [`docs/adapters/claude.md`](docs/adapters/claude.md).

Control (optional; same CLI as Cursor slash commands):

- [ ] **MCP** — Register `aftertone.mcp_server` in Claude’s MCP config; point `uv run --directory <install>/py` at the global install root (see template JSON above).
- [ ] **MCP parity** — Extend `mcp_server.py` tools to match `python -m aftertone` (`restart`, `repair`, `set lang|speed|mode|voice`, …) or generate tools from CLI subparsers so MCP and slash commands do not drift.
- [ ] **Do not** rely on MCP alone for post-reply speech — hooks (or equivalent lifecycle) must run every turn; agents may skip MCP tools.

Docs / PR:

- [x] README adapter row + Claude quickstart — [`docs/adapters/claude.md`](docs/adapters/claude.md), site docs, slash commands (`/aftertone_*`).
- [x] Adapter shipped on `main` (global **Stop** hook + slash commands); follow-ups welcome for MCP and edge cases.

## OpenAI Codex — contributor todos

Speech (required):

- [x] **Research** — Codex `Stop` hook with `last_assistant_message`; see [`docs/adapters/codex.md`](docs/adapters/codex.md).
- [x] **Payload** — Codex `Stop` accepted by shared `prepare.py` / `hook_run` pipeline.
- [x] **Install path** — Global install writes `~/.codex/hooks.json` and Unix/Windows wrappers.
- [x] **Config** — Shared `speak_summary.toml` under install `.cursor/hooks/`.
- [x] **Model guidance** — `~/.codex/AGENTS.md` on install; language-synced spoken-summary rule.
- [x] **Smoke test** — synthetic Codex `Stop` payload and real-session steps documented in [`docs/adapters/codex.md`](docs/adapters/codex.md).

Control (optional):

- [ ] **MCP** — Ship Codex MCP config snippet (install-root `py`, `python -m aftertone.mcp_server`) alongside speech adapter docs.
- [ ] **MCP parity** — Same as Claude: full CLI surface via MCP tools; speech still via hook only.
- [ ] **Do not** use MCP as the only way to speak after each reply.

Docs / PR:

- [x] README adapter row + Codex setup — [`docs/adapters/codex.md`](docs/adapters/codex.md).
- [x] Adapter shipped on `main` (global `Stop` hook + guidance); follow-ups welcome for MCP and edge cases.

## Principles

- **Privacy first:** default path stays localhost; no cloud TTS in core.
- **Thin adapters:** keep IDE/CLI glue small; reuse `py/speak_summary_prepare.py` and `tts_daemon.py`.
- **One speakable line:** prefer `<spoken_summary>` in model output (see `.cursor/rules/spoken-summary.mdc` for Cursor; mirror the idea elsewhere).

## Dev setup

```bash
bash scripts/bootstrap.sh
cd py && uv run python tts_daemon_ctl.py start --repo-root ..
bash py/test_speak_summary_pipeline.sh   # needs ./assets/onnx + audio
```

## Pull requests

- One logical change per PR when possible.
- Run the smoke script above before claiming audio/hook fixes.
- For new adapters, add a short **doc section** in README + a row in the table above.

## Questions

Open a **Discussion** or **Issue** with the tool you’re targeting (Claude / Codex / other) and a link to any public hook or event API you’ve found — maintainers will triage.

## Starter work

Look for labels **`good first issue`** and **`help wanted`**. Suggested titles and bodies (if you want to open a fresh issue yourself) live in **[.github/STARTER_ISSUES.md](.github/STARTER_ISSUES.md)**.
