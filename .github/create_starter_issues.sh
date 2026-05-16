#!/usr/bin/env bash
# Create starter GitHub issues (requires: gh auth login, push access to omarelkhal/aftertone).
set -euo pipefail
cd "$(dirname "$0")/.."

if ! gh auth status &>/dev/null; then
  echo "Run: gh auth login" >&2
  exit 1
fi

gh label create "adapter" --color "D93F0B" --description "IDE/CLI integration" 2>/dev/null || true

# Re-running may create duplicate issues; close extras manually if needed.

gh issue create \
  --title "docs: Windows and WSL playback notes for tts_daemon" \
  --label "documentation,good first issue" \
  --body "## Scope
Document how \`tts_io\` chooses \`sounddevice\` vs \`aplay\` on Windows and WSL2, and common failure modes (no PortAudio, WSL audio bridge).

## Acceptance
- [ ] New subsection in \`py/README.md\` or root \`README.md\`
- [ ] Link to upstream PortAudio / Cursor docs where useful"

gh issue create \
  --title "docs: optional CUDA / onnxruntime-gpu for tts_daemon" \
  --label "documentation,good first issue" \
  --body "## Scope
Short section: install \`onnxruntime-gpu\`, set \`use_gpu = true\` in \`speak_summary.toml\`, verify providers in daemon logs.

## Acceptance
- [ ] \`py/README.md\` (or \`AGENTS.md\`) updated
- [ ] No change to default CPU path"

gh issue create \
  --title "[adapter] Claude Code: capture final assistant text for TTS" \
  --label "adapter,help wanted" \
  --body "## Goal
Design how to get the same JSON shape \`speak_summary_prepare.py\` expects (or POST directly to \`/say\`) from Claude Code after a reply completes.

## Deliverable
Links to official docs / events, proposed flow, and risks — PR can be docs-only for the first merge.

See CONTRIBUTING table row **Claude Code**."

gh issue create \
  --title "[adapter] OpenAI Codex: lifecycle hook or wrapper for /say" \
  --label "adapter,help wanted" \
  --body "## Goal
Research Codex CLI or IDE extension points for \"response finished\" and how to pipe a short string to localhost.

## Deliverable
Design note in \`docs/\` or issue thread; optional proof-of-concept script.

See CONTRIBUTING table row **OpenAI Codex**."

gh issue create \
  --title "Packaging: pip-installable aftertone daemon (spike)" \
  --label "enhancement,help wanted" \
  --body "## Goal
Explore \`pyproject.toml\` entry points for \`aftertone-daemon\` / \`aftertone-ctl\` without breaking repo-relative asset paths.

## Acceptance
- [ ] Issue comment or small ADR with recommendation
- [ ] No obligation to merge full packaging in the first PR"

echo "Done. gh issue list --limit 10"
