# Contributing to Aftertone

Thanks for helping make **local, private “hear the gist”** work across more than one tool.

## Community

- This project follows the **[Code of Conduct](CODE_OF_CONDUCT.md)**. By participating, you agree to uphold it.
- **Issues:** use [GitHub Issues](https://github.com/omarelkhal/aftertone/issues) and pick a template (**Bug report**, **Feature or idea**, **Adapter research**) so we can triage quickly.

## What we’re building

| Area | Status | Help wanted |
|------|--------|-------------|
| **Cursor** `afterAgentResponse` + `tts_daemon` | Shipped | Bugfixes, docs, Windows audio edge cases |
| **Claude Code** (or Claude Desktop hooks) | Not shipped | Design + PR: how to get “final assistant text” JSON to `speak_summary_prepare.py` or `POST /say` |
| **OpenAI Codex** (CLI / IDE) | Not shipped | Design + PR: lifecycle hook or wrapper that POSTs short text to the daemon |
| **Core** daemon + ONNX pipeline | Shipped | Performance, GPU docs, packaging |

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
