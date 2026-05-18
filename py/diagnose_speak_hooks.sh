#!/usr/bin/env bash
# Show recent Cursor hook diagnostics (after a real agent turn, reload Cursor if you changed hooks.json).
# Usage: bash py/diagnose_speak_hooks.sh   (from repo root)

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ST="${REPO}/.cursor/hooks/state"
echo "=== last 15 lines: hook_payload_trace.jsonl (did Cursor run afterAgentResponse / stop?) ==="
tail -15 "${ST}/hook_payload_trace.jsonl" 2>/dev/null || echo "(missing — no hook ran yet)"
echo ""
echo "=== last 20 lines: speak_summary-hook.log ==="
tail -20 "${ST}/speak_summary-hook.log" 2>/dev/null || echo "(missing)"

export DIAG_REPO="${REPO}"
# shellcheck source=../.cursor/hooks/venv_python.sh
source "${REPO}/.cursor/hooks/venv_python.sh"
vpy=""
if vpy="$(aftertone_venv_python "${REPO}/py")"; then
  "${vpy}" "${REPO}/py/diagnose_speak_hooks_report.py"
else
  echo ""
  echo "(Install venv: cd py && uv sync — then verdict script can run.)"
fi

echo ""
echo "Tip: run one Agent message in Cursor, wait until the reply FINISHES, then re-run:"
echo "  bash py/diagnose_speak_hooks.sh"
echo "You want a NEW line with a fresh timestamp and a generation_id that is NOT pipeline-test."
