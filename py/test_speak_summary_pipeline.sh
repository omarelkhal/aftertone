#!/usr/bin/env bash
# End-to-end test: same bash hook Cursor runs on afterAgentResponse (inline text).
# Usage (from anywhere):
#   bash /path/to/supertonic/py/test_speak_summary_pipeline.sh
# Exit 0 on success, 1 on failure.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${REPO}/py"
HOOK_SH="${REPO}/.cursor/hooks/speak_summary.sh"

# shellcheck source=../.cursor/hooks/venv_python.sh
source "${REPO}/.cursor/hooks/venv_python.sh"
VENV_PY=""
if ! VENV_PY="$(aftertone_venv_python "${PY}")"; then
  echo "FAIL: ${PY}/.venv python missing. Run: cd py && uv sync"
  exit 1
fi
if [[ ! -f "${HOOK_SH}" ]]; then
  echo "FAIL: hook script missing: ${HOOK_SH}"
  exit 1
fi

MARK="$(date -u +"%Y-%m-%dT%H:%M:%S")"
HOOK_JSON='{"hook_event_name":"afterAgentResponse","text":"Pipeline test reply. It includes \"quotes\" and enough letters to pass min_chars.","generation_id":"pipeline-test","conversation_id":"c-pipeline"}'

export AFTERTONE_REPO="${REPO}"
export SUPERTONIC_REPO="${REPO}"
printf '%s' "${HOOK_JSON}" | bash "${HOOK_SH}"

# Same as py/.cursor/hooks.json: workspace root = py/, cwd = py/
(cd "${PY}" && printf '%s' "${HOOK_JSON}" | bash ../.cursor/hooks/speak_summary.sh)

LOG="${REPO}/.cursor/hooks/state/speak_summary-hook.log"
TAIL="$(tail -80 "${LOG}")"
if ! grep -q "prepare_ok" <<<"${TAIL}"; then
  echo "FAIL: no prepare_ok in ${LOG}"
  tail -20 "${LOG}"
  exit 1
fi
if [[ "$(grep -c "prepare_ok" <<<"${TAIL}")" -lt 2 ]]; then
  echo "FAIL: expected two prepare_ok lines (repo hook + py-cwd hook), log tail:"
  grep prepare_ok <<<"${TAIL}" || true
  exit 1
fi
if ! grep -q "post_say_done" <<<"${TAIL}"; then
  echo "FAIL: no post_say_done in ${LOG}"
  tail -20 "${LOG}"
  exit 1
fi

SPOKEN_DIR="${REPO}/.cursor/hooks/state/spoken"
if ! grep -rq "pipeline-test" "${SPOKEN_DIR}" 2>/dev/null; then
  echo "FAIL: generation_id pipeline-test not found under ${SPOKEN_DIR}"
  exit 1
fi

TRACE="${REPO}/.cursor/hooks/state/hook_payload_trace.jsonl"
LAST="$(tail -1 "${TRACE}" 2>/dev/null || echo "")"
if [[ -z "${LAST}" ]]; then
  echo "FAIL: no hook_payload_trace.jsonl tail (trace not written?)"
  exit 1
fi
if ! echo "${LAST}" | "${VENV_PY}" -c "import json,sys; d=json.load(sys.stdin); assert d.get('inline_after_response_ok') is True"; then
  echo "FAIL: last trace line should have inline_after_response_ok true: ${LAST}"
  exit 1
fi

# stop hook trace only (no speech): same shape as Cursor stop payload
STOP_JSON='{"hook_event_name":"stop","status":"completed","loop_count":0,"generation_id":"stop-trace-test"}'
printf '%s' "${STOP_JSON}" | bash "${REPO}/.cursor/hooks/hook_payload_trace.sh"
STOP_LAST="$(tail -1 "${TRACE}")"
if ! echo "${STOP_LAST}" | "${VENV_PY}" -c "import json,sys; d=json.load(sys.stdin); assert d.get('hook_event_name')=='stop' and d.get('status')=='completed'"; then
  echo "FAIL: stop trace line unexpected: ${STOP_LAST}"
  exit 1
fi

echo "OK: speak_summary pipeline (afterAgentResponse + daemon + POST /say). Mark=${MARK}"
exit 0
