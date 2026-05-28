# Codex adapter

Aftertone speaks after each Codex turn via a global user `Stop` hook in `~/.codex/hooks.json` and the shared local `tts_daemon` install.

Codex hook reference: https://developers.openai.com/codex/hooks

## Layout

| Path | Purpose |
|------|---------|
| `~/aftertone` (default) | Runtime from `scripts/install.sh` - ONNX assets, daemon, shared config |
| `~/.codex/hooks.json` | Codex `Stop` hook that calls Aftertone after each turn |
| `~/.codex/AGENTS.md` | Codex-facing spoken-summary guidance |
| `~/.codex/commands/aftertone-*.md` | Codex command docs for `on`, `off`, and `status` |
| `~/.cursor/hooks/aftertone-codex-speak-on-stop.*` | Wrapper script copied by install |
| `~/aftertone/.cursor/hooks/speak_summary.toml` | Shared Aftertone config across adapters |

## Install

Run the normal global install:

```bash
curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash -s -- --install-uv --start-daemon
```

On Windows:

```powershell
irm https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.ps1 | iex
```

Global install registers Cursor, Claude Code, and Codex assets when their config locations are available.

## Trust / Review

Codex requires non-managed hooks to be reviewed or trusted. After install, review the hook entry in `~/.codex/hooks.json`. It should call an Aftertone wrapper named `aftertone-codex-speak-on-stop`.

The hook reads Codex `Stop` JSON on stdin and returns JSON or empty output, as required by Codex.

## Daily Use

Start Codex normally:

```bash
codex
```

Enable speech for the current Codex session:

```bash
uv run --directory ~/aftertone/py python -m aftertone on
```

Then send one Codex reply that includes a short `<spoken_summary>` tag. The next `Stop` hook registers this Codex session id on the allowlist. Other sessions stay silent until enabled there too.

Turn off this session:

```bash
uv run --directory ~/aftertone/py python -m aftertone off
```

Check status:

```bash
uv run --directory ~/aftertone/py python -m aftertone status
```

## Spoken Text

With default `summary_mode = "tag_only"` and `only_speak_spoken_summary = true`, Codex replies must end substantive messages with:

```xml
<spoken_summary>
The Codex session is ready to speak after each reply!!
</spoken_summary>
```

The tag language must match `lang` in `speak_summary.toml`. The hook does not translate.

## Synthetic Smoke Test

From the install root:

```bash
cd "$(cat ~/.cursor/hooks/aftertone-install-dir)"
printf '%s' '{"hook_event_name":"Stop","session_id":"codex-smoke","turn_id":"turn-smoke","model":"gpt-5.1-codex","permission_mode":"default","cwd":"/tmp/aftertone","last_assistant_message":"Smoke test.\n\n<spoken_summary>The Codex Stop hook smoke test reached prepare!!</spoken_summary>"}' \
  | AFTERTONE_INSTALL_DIR="$PWD" uv run --directory py python speak_summary_prepare.py
```

Expected output includes:

```json
{"text":"The Codex Stop hook smoke test reached prepare!!"}
```

No-tag check:

```bash
printf '%s' '{"hook_event_name":"Stop","session_id":"codex-smoke","turn_id":"turn-smoke-2","model":"gpt-5.1-codex","permission_mode":"default","cwd":"/tmp/aftertone","last_assistant_message":"Smoke test without a spoken tag."}' \
  | AFTERTONE_INSTALL_DIR="$PWD" uv run --directory py python speak_summary_prepare.py
```

Expected output:

```json
{}
```

## Real Codex Verification

1. Start or check the daemon:

   ```bash
   uv run --directory ~/aftertone/py python -m aftertone status
   ```

2. Enable this session:

   ```bash
   uv run --directory ~/aftertone/py python -m aftertone on
   ```

3. In Codex, ask for a tiny response that ends with:

   ```xml
   <spoken_summary>
   Codex and Aftertone are connected for this session!!
   </spoken_summary>
   ```

4. Confirm the session id was registered:

   ```bash
   uv run --directory ~/aftertone/py python -m aftertone session list
   ```

## Troubleshooting

- Nothing speaks: run `uv run --directory ~/aftertone/py python -m aftertone doctor`, then inspect `.cursor/hooks/state/speak_summary-hook.log`.
- Hook not running: review or trust the `~/.codex/hooks.json` entry. Codex project hooks may require trust per the Codex hooks docs.
- No tag, no speech: default mode is tag-only.
- Wrong language: write the tag in the TOML `lang`; run `/aftertone-lang` or `sync_spoken_rule_lang.py` after language changes.
- MCP is optional control only. Post-reply speech comes from the Codex `Stop` hook.

## Status

Codex global `Stop` hooks, guidance, and command docs ship with global install. MCP control snippets remain optional follow-up work.
