# Codex Public Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish user-facing Codex adapter docs and smoke-test instructions now that the Codex hook path, installer, and guidance assets are implemented.

**Architecture:** Add `docs/adapters/codex.md` as the canonical Codex setup page. Update README, site docs, and CONTRIBUTING status to mark Codex shipped while keeping MCP as optional follow-up. Keep smoke tests local and deterministic: first synthetic `Stop` payload through `speak_summary_prepare.py`, then real Codex turn verification.

**Tech Stack:** Markdown docs, static HTML docs site, existing Aftertone CLI, official Codex hooks docs at https://developers.openai.com/codex/hooks.

---

## File Structure

- Create `docs/adapters/codex.md`
  - Install result, Codex hook contract, trust review, daily use, per-session on/off, smoke tests, troubleshooting, source links.
- Modify `README.md`
  - Mark Codex as shipped.
  - Add Codex quickstart row and guide link.
  - Add Codex command/control mention without bloating the README.
- Modify `docs/docs.html`
  - Add Codex setup section.
  - Add Codex sidebar link.
  - Add Codex slash/control docs.
  - Add Codex troubleshooting/smoke test references.
- Modify `docs/index.html`
  - Update homepage status copy from “roadmap” to Cursor, Claude Code, and Codex.
- Modify `CONTRIBUTING.md`
  - Mark Codex speech requirements as shipped.
  - Keep MCP as optional follow-up.
- Modify `docs/README.md`
  - List the new Codex adapter doc.

## Task 1: Add Codex Adapter Guide

**Files:**
- Create: `docs/adapters/codex.md`

- [ ] **Step 1: Create adapter guide**

Create `docs/adapters/codex.md`:

```markdown
# Codex adapter

Aftertone speaks after each Codex turn via a global user `Stop` hook in `~/.codex/hooks.json` and the shared local `tts_daemon` install.

Codex hook reference: https://developers.openai.com/codex/hooks

## Layout

| Path | Purpose |
|------|---------|
| `~/aftertone` (default) | Runtime from `scripts/install.sh` — ONNX assets, daemon, shared config |
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

## Trust / review

Codex requires non-managed hooks to be reviewed or trusted. After install, review the hook entry in `~/.codex/hooks.json`. It should call an Aftertone wrapper named `aftertone-codex-speak-on-stop`.

The hook reads Codex `Stop` JSON on stdin and returns JSON/empty output, as required by Codex.

## Daily use

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

## Spoken text

With default `summary_mode = "tag_only"` and `only_speak_spoken_summary = true`, Codex replies must end substantive messages with:

```xml
<spoken_summary>
The Codex session is ready to speak after each reply!!
</spoken_summary>
```

The tag language must match `lang` in `speak_summary.toml`. The hook does not translate.

## Synthetic smoke test

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

## Real Codex verification

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
```

- [ ] **Step 2: Commit Task 1**

```bash
git add docs/adapters/codex.md
git commit -m "docs(codex): add adapter guide"
```

## Task 2: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README adapter status and links**

In `README.md`, change the adapter table Codex status from `soon` to `✅`.

Change:

```markdown
Same `tts_daemon` for all — each adapter runs a hook when a reply finishes. [Claude setup](docs/adapters/claude.md) · [Contributing](CONTRIBUTING.md)
```

To:

```markdown
Same `tts_daemon` for all — each adapter runs a hook when a reply finishes. [Claude setup](docs/adapters/claude.md) · [Codex setup](docs/adapters/codex.md) · [Contributing](CONTRIBUTING.md)
```

- [ ] **Step 2: Add Codex quickstart row**

In the "Then" table, add:

```markdown
| **Codex** | `codex` → `uv run --directory ~/aftertone/py python -m aftertone on`, then review/trust `~/.codex/hooks.json` |
```

- [ ] **Step 3: Add Codex control row**

In the per-session control table, change the table from two columns to three columns:

```markdown
| Cursor | Claude Code | Codex |
|--------|-------------|-------|
| `/aftertone-on` `/aftertone-off` `/aftertone-toggle` | `/aftertone_on` `/aftertone_off` `/aftertone_toggle` | `python -m aftertone on` / `off` / `toggle` |
| `/aftertone-status` | `/aftertone_status` | `python -m aftertone status` |
| `/aftertone-lang` `/aftertone-voice` `/aftertone-restart` | `/aftertone_lang` `/aftertone_voice` `/aftertone_restart` | `python -m aftertone set ...` / `restart` |
| … [docs](https://omarelkhal.github.io/aftertone/docs.html#slash-commands) | … [Claude guide](docs/adapters/claude.md) | … [Codex guide](docs/adapters/codex.md) |
```

- [ ] **Step 4: Commit Task 2**

```bash
git add README.md
git commit -m "docs(readme): mark Codex adapter shipped"
```

## Task 3: Update CONTRIBUTING

**Files:**
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Mark Codex shipped in overview**

Change the Codex row to:

```markdown
| **OpenAI Codex** (`Stop` hook + guidance) | Shipped — [docs/adapters/codex.md](docs/adapters/codex.md) | Optional MCP control and edge-case docs |
```

- [ ] **Step 2: Mark required Codex speech checklist shipped**

Under "OpenAI Codex — contributor todos", change required speech items to checked and reference `docs/adapters/codex.md`:

```markdown
- [x] **Research** — Codex `Stop` hook with `last_assistant_message`; see [`docs/adapters/codex.md`](docs/adapters/codex.md).
- [x] **Payload** — Codex `Stop` accepted by shared `prepare.py` / `hook_run` pipeline.
- [x] **Install path** — Global install writes `~/.codex/hooks.json` and Unix/Windows wrappers.
- [x] **Config** — Shared `speak_summary.toml` under install `.cursor/hooks/`.
- [x] **Model guidance** — `~/.codex/AGENTS.md` on install; language-synced spoken-summary rule.
- [x] **Smoke test** — synthetic Codex `Stop` payload and real-session steps documented in [`docs/adapters/codex.md`](docs/adapters/codex.md).
```

Keep MCP items unchecked.

- [ ] **Step 3: Update docs/PR subsection**

Change:

```markdown
- [ ] README adapter row + “Codex setup” when hook path is proven.
- [ ] Docs-only research PR welcome first.
```

To:

```markdown
- [x] README adapter row + Codex setup — [`docs/adapters/codex.md`](docs/adapters/codex.md).
- [x] Adapter shipped on `main` (global `Stop` hook + guidance); follow-ups welcome for MCP and edge cases.
```

- [ ] **Step 4: Commit Task 3**

```bash
git add CONTRIBUTING.md
git commit -m "docs(contributing): mark Codex adapter shipped"
```

## Task 4: Update Docs Site

**Files:**
- Modify: `docs/docs.html`
- Modify: `docs/index.html`
- Modify: `docs/README.md`

- [ ] **Step 1: Update docs sidebar and getting started**

In `docs/docs.html`, add a sidebar link after Claude/Cursor relevant links:

```html
<a href="#codex">Codex setup</a>
```

In the getting-started intro, mention Codex hooks:

```html
It installs <strong>uv</strong>, Python, ONNX models, Cursor / Claude / Codex hooks, the daemon, and enables spoken TTS...
```

- [ ] **Step 2: Add Codex getting-started section**

After the Claude Code "Then" section, add:

```html
<h3>Then in Codex</h3>
<ul style="color: var(--muted); line-height: 1.75; margin-bottom: 2rem;">
  <li>Run <code>codex</code> normally.</li>
  <li>Review or trust the installed <code>~/.codex/hooks.json</code> entry if Codex prompts for hook trust.</li>
  <li>Enable this session with <code>uv run --directory ~/aftertone/py python -m aftertone on</code>.</li>
  <li>Send one reply with a <code>&lt;spoken_summary&gt;</code> tag so the Stop hook registers the session id.</li>
</ul>
```

- [ ] **Step 3: Add Codex control section**

After the Claude slash commands section, add:

```html
<h3 id="slash-codex">Codex (CLI control)</h3>
<p>Global install registers a Codex <strong>Stop</strong> hook in <code>~/.codex/hooks.json</code>, plus guidance in <code>~/.codex/AGENTS.md</code>. Codex control uses the Aftertone CLI from the install root.</p>
<div class="table-wrap">
  <table>
    <thead>
      <tr><th>Command</th><th>What it does</th></tr>
    </thead>
    <tbody>
      <tr><td><code>python -m aftertone on</code> · <code>off</code></td><td>Enable or disable spoken TTS for the current Codex session</td></tr>
      <tr><td><code>python -m aftertone status</code></td><td>Show config, daemon, and enabled sessions</td></tr>
      <tr><td><code>python -m aftertone session list</code></td><td>Confirm the Codex session id was registered</td></tr>
    </tbody>
  </table>
</div>
<p>Guide on GitHub: <a href="https://github.com/omarelkhal/aftertone/blob/main/docs/adapters/codex.md">docs/adapters/codex.md</a></p>
```

- [ ] **Step 4: Add Codex setup section**

After the Cursor setup section, add:

```html
<h2 id="codex">Codex setup</h2>
<p>Codex uses the official <a href="https://developers.openai.com/codex/hooks" rel="noopener noreferrer">Codex hooks</a> <code>Stop</code> event. Aftertone reads <code>last_assistant_message</code> from the hook JSON and passes it through the shared local TTS pipeline.</p>
<div class="callout callout-tip">
  <strong>Verify Codex locally</strong>
  Run the synthetic <code>Stop</code> payload smoke test in <a href="https://github.com/omarelkhal/aftertone/blob/main/docs/adapters/codex.md">docs/adapters/codex.md</a>, then test one real Codex reply with a <code>&lt;spoken_summary&gt;</code> tag.
</div>
```

- [ ] **Step 5: Update homepage copy**

In `docs/index.html`, replace the sentence:

```html
Cursor <code>afterAgentResponse</code> and Claude Code <strong>Stop</strong> hooks — same daemon. Codex and OpenCode on the roadmap.
```

With:

```html
Cursor <code>afterAgentResponse</code>, Claude Code <strong>Stop</strong>, and Codex <strong>Stop</strong> hooks — same daemon. OpenCode is on the roadmap.
```

- [ ] **Step 6: Update docs README**

In `docs/README.md`, add:

```markdown
- `adapters/codex.md` — Codex adapter (global Stop hook + smoke test)
```

- [ ] **Step 7: Commit Task 4**

```bash
git add docs/docs.html docs/index.html docs/README.md
git commit -m "docs(site): add Codex setup"
```

## Task 5: Verification and Issue Update

**Files:**
- Verify only unless checks reveal a problem.

- [ ] **Step 1: Run docs text checks**

Run:

```bash
grep -RIn "Codex" README.md CONTRIBUTING.md docs/adapters/codex.md docs/docs.html docs/index.html docs/README.md
grep -RIn "Codex.*soon\\|roadmap" README.md CONTRIBUTING.md docs docs/index.html || true
```

Expected: Codex is linked as shipped in README/docs/CONTRIBUTING. Remaining "roadmap" mentions should not say Codex is unshipped.

- [ ] **Step 2: Run smoke prepare command**

Run:

```bash
printf '%s' '{"hook_event_name":"Stop","session_id":"codex-smoke","turn_id":"turn-smoke","model":"gpt-5.1-codex","permission_mode":"default","cwd":"/tmp/aftertone","last_assistant_message":"Smoke test.\n\n<spoken_summary>The Codex Stop hook smoke test reached prepare!!</spoken_summary>"}' \
  | AFTERTONE_INSTALL_DIR="$PWD" uv run --directory py python speak_summary_prepare.py
```

Expected: JSON contains `"text": "The Codex Stop hook smoke test reached prepare!!"`.

- [ ] **Step 3: Run no-tag smoke command**

Run:

```bash
printf '%s' '{"hook_event_name":"Stop","session_id":"codex-smoke","turn_id":"turn-smoke-2","model":"gpt-5.1-codex","permission_mode":"default","cwd":"/tmp/aftertone","last_assistant_message":"Smoke test without a spoken tag."}' \
  | AFTERTONE_INSTALL_DIR="$PWD" uv run --directory py python speak_summary_prepare.py
```

Expected: `{}`.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py tests/test_uninstall_global_hooks.py tests/test_sync_spoken_rule_lang.py tests/test_aftertone_v2.py -q
```

Expected: PASS.

- [ ] **Step 5: Run diff checks**

Run:

```bash
git diff --check
grep -RIn --exclude-dir=.venv -E '^<<<<<<<|^=======|^>>>>>>>' README.md CONTRIBUTING.md docs py scripts || true
```

Expected: clean.

- [ ] **Step 6: Comment on issue #18**

Run:

```bash
gh issue comment 18 --body "Implemented and verified locally:

- Added \`docs/adapters/codex.md\` with install, trust, daily use, troubleshooting, synthetic Stop smoke test, and real Codex verification.
- Updated README, docs site, homepage copy, and CONTRIBUTING to mark Codex shipped.
- Verified synthetic Codex Stop payload returns a /say payload and no-tag payload returns \`{}\`.
- Focused tests pass.
- \`git diff --check\` clean.

Docs cite the official Codex hooks page: https://developers.openai.com/codex/hooks"
```

- [ ] **Step 7: Commit the implementation plan**

```bash
git add docs/superpowers/plans/2026-05-28-codex-public-docs.md
git commit -m "docs: plan Codex public docs"
```

## Self-Review

- Spec coverage: This plan covers `docs/adapters/codex.md`, README/site shipped status, CONTRIBUTING shipped checklist, synthetic and real smoke tests, and citation of official Codex hooks docs.
- Placeholder scan: No task contains TBD/TODO/later/fill-in instructions.
- Type consistency: The smoke commands use `speak_summary_prepare.py`, `AFTERTONE_INSTALL_DIR`, and Codex `Stop` fields consistently with the implemented adapter.
