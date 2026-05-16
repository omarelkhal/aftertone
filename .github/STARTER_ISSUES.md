# Suggested starter issues

Maintainers can **`gh issue create`** from these, or contributors can open a matching issue / PR.

---

## 1. Windows / WSL audio notes (`good first issue`, `documentation`)

**Title:** `docs: Windows and WSL playback notes for tts_daemon`

**Body:**

```markdown
## Scope
Document how `tts_io` chooses `sounddevice` vs `aplay` on Windows and WSL2, and common failure modes (no PortAudio, WSL audio bridge).

## Acceptance
- [ ] New subsection in `py/README.md` or root `README.md`
- [ ] Link to upstream PortAudio / Cursor docs where useful
```

---

## 2. GPU / `onnxruntime-gpu` (`good first issue`, `documentation`)

**Title:** `docs: optional CUDA / onnxruntime-gpu for tts_daemon`

**Body:**

```markdown
## Scope
Short section: install `onnxruntime-gpu`, set `use_gpu = true` in `speak_summary.toml`, verify providers in daemon logs.

## Acceptance
- [ ] `py/README.md` (or `AGENTS.md`) updated
- [ ] No change to default CPU path
```

---

## 3. Claude Code adapter — research (`help wanted`, `adapter`)

**Title:** `[adapter] Claude Code: capture final assistant text for TTS`

**Body:**

```markdown
## Goal
Design how to get the same JSON shape `speak_summary_prepare.py` expects (or POST directly to `/say`) from Claude Code after a reply completes.

## Deliverable
Links to official docs / events, proposed flow, and risks — PR can be docs-only for the first merge.

See CONTRIBUTING table row **Claude Code**.
```

---

## 4. OpenAI Codex adapter — research (`help wanted`, `adapter`)

**Title:** `[adapter] OpenAI Codex: lifecycle hook or wrapper for /say`

**Body:**

```markdown
## Goal
Research Codex CLI or IDE extension points for “response finished” and how to pipe a short string to localhost.

## Deliverable
Design note in `docs/` or issue thread; optional proof-of-concept script.

See CONTRIBUTING table row **OpenAI Codex**.
```

---

## 5. Packaging spike (`help wanted`, `enhancement`)

**Title:** `Packaging: pip-installable aftertone daemon (spike)`

**Body:**

```markdown
## Goal
Explore `pyproject.toml` entry points for `aftertone-daemon` / `aftertone-ctl` without breaking repo-relative asset paths.

## Acceptance
- [ ] Issue comment or small ADR with recommendation
- [ ] No obligation to merge full packaging in the first PR
```

---

## Batch-create with `gh` (optional)

Create labels once (ignore errors if they already exist):

```bash
gh label create "adapter" --color "D93F0B" --description "IDE/CLI integration" 2>/dev/null || true
```

Then open each issue in the GitHub UI, or run **`bash .github/create_starter_issues.sh`** once (requires `gh auth login`; re-run may duplicate issues).
