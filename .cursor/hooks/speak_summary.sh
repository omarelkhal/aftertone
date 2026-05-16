#!/usr/bin/env bash
# Aftertone / Cursor hook: speak a short summary via tts_daemon (afterAgentResponse preferred — has inline `text`;
# `stop` often lacks transcript_path). See speak_summary_prepare.py.
# Never fails the hook: always exits 0.
#
# If nothing speaks, check:
#   tail -50 .cursor/hooks/state/speak_summary-hook.log
#   tail -50 .cursor/hooks/state/speak_summary-prepare.stderr.log
# Run once: cd py && uv sync   (creates py/.venv so hooks work without `uv` on GUI PATH)

set -uo pipefail

# Resolve Aftertone repo root whether this file lives at <repo>/.cursor/hooks/ or <repo>/py/.cursor/hooks/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${SCRIPT_DIR}"
while [[ "${REPO}" != "/" ]]; do
  if [[ -f "${REPO}/py/speak_summary_prepare.py" ]]; then
    break
  fi
  REPO="$(dirname "${REPO}")"
done
if [[ ! -f "${REPO}/py/speak_summary_prepare.py" ]]; then
  mkdir -p "${SCRIPT_DIR}/../hooks/state"
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") speak_summary: could not find repo (no py/speak_summary_prepare.py above ${SCRIPT_DIR})" >>"${SCRIPT_DIR}/../hooks/state/speak_summary-hook.log" || true
  exit 0
fi
export AFTERTONE_REPO="${REPO}"
export SUPERTONIC_REPO="${REPO}" # legacy alias for scripts / forks
PY="${REPO}/py"
PORT_FILE="${REPO}/.cursor/hooks/state/tts-daemon.port"
STATE_DIR="${REPO}/.cursor/hooks/state"
LOG="${STATE_DIR}/speak_summary-hook.log"
PREP_ERR="${STATE_DIR}/speak_summary-prepare.stderr.log"
mkdir -p "${STATE_DIR}"

# Cursor GUI often has a minimal PATH (no uv, no cargo bin). Prefer project venv.
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:/usr/local/bin:/opt/homebrew/bin:${PATH}"

log() {
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") $*" >>"${LOG}"
}

HOOK_JSON="$(cat || true)"
printf '%s' "${HOOK_JSON}" | "${PY}/.venv/bin/python" "${PY}/hook_payload_trace.py" "${STATE_DIR}/hook_payload_trace.jsonl" 2>/dev/null || true
log "hook_invoked hook_json_bytes=${#HOOK_JSON}"

read_port() {
  local toml="${REPO}/.cursor/hooks/speak_summary.toml"
  local toml_port=""
  if [[ -f "${toml}" ]]; then
    toml_port="$(grep -E '^[[:space:]]*port[[:space:]]*=' "${toml}" | head -1 | sed -E 's/.*=[[:space:]]*//' | tr -d ' \"')"
  fi
  if [[ -f "${PORT_FILE}" ]]; then
    local file_port
    file_port="$(tr -d ' \n\r' <"${PORT_FILE}")"
    if [[ -n "${toml_port}" ]] && [[ -n "${file_port}" ]] && [[ "${toml_port}" != "${file_port}" ]] &&
      [[ "${toml_port}" =~ ^[0-9]+$ ]] && [[ "${file_port}" =~ ^[0-9]+$ ]]; then
      log "port_mismatch toml_port=${toml_port} state_file_port=${file_port} hint=restart_daemon_cd_py_uv_run_tts_daemon_ctl_restart"
    fi
    echo "${file_port}"
    return
  fi
  if [[ -n "${toml_port}" ]] && [[ "${toml_port}" =~ ^[0-9]+$ ]]; then
    echo "${toml_port}"
    return
  fi
  echo "8765"
}

run_prepare() {
  : >"${PREP_ERR}"
  if [[ -x "${PY}/.venv/bin/python" ]]; then
    printf '%s' "${HOOK_JSON}" | "${PY}/.venv/bin/python" "${PY}/speak_summary_prepare.py" 2>>"${PREP_ERR}"
    return $?
  fi
  if command -v uv >/dev/null 2>&1; then
    printf '%s' "${HOOK_JSON}" | (cd "${PY}" && uv run python speak_summary_prepare.py) 2>>"${PREP_ERR}"
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "${HOOK_JSON}" | PYTHONPATH="${PY}" python3 "${PY}/speak_summary_prepare.py" 2>>"${PREP_ERR}"
    return $?
  fi
  log "prepare_skip no_python venv_missing=${PY}/.venv/bin/python uv_missing=1"
  echo '{}'
  return 1
}

ensure_daemon() {
  local port="$1"
  if curl -fsS -m 0.35 "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1; then
    return 0
  fi
  log "daemon_bootstrap port=${port}"
  if [[ -x "${PY}/.venv/bin/python" ]]; then
    "${PY}/.venv/bin/python" "${PY}/tts_daemon_ctl.py" start --repo-root "${REPO}" >>"${STATE_DIR}/tts-daemon-bootstrap.log" 2>&1 || true
  elif command -v uv >/dev/null 2>&1; then
    (cd "${PY}" && uv run python tts_daemon_ctl.py start --repo-root "${REPO}") >>"${STATE_DIR}/tts-daemon-bootstrap.log" 2>&1 || true
  else
    log "daemon_bootstrap_failed no_uv_no_venv"
  fi
  sleep 0.5
}

post_say() {
  local port="$1"
  local payload="$2"
  local tmp
  tmp="$(mktemp "${STATE_DIR}/say_payload.XXXXXX.json")"
  printf '%s' "${payload}" >"${tmp}"
  if ! curl -fsS -m 3 -X POST "http://127.0.0.1:${port}/say" \
    -H "Content-Type: application/json" \
    --data-binary @"${tmp}" >/dev/null 2>&1; then
    log "post_say_failed port=${port}"
  fi
  rm -f "${tmp}"
}

PAYLOAD="$(run_prepare || true)"
PAYLOAD="$(echo "${PAYLOAD}" | tr -d '\n\r' | head -c 8000)"
if [[ "${PAYLOAD}" != "{"* ]]; then
  log "prepare_bad_output first_bytes=${PAYLOAD:0:120}"
  PAYLOAD='{}'
fi
if [[ "${PAYLOAD}" == "{}" ]] || [[ -z "${PAYLOAD}" ]]; then
  if [[ -s "${PREP_ERR}" ]]; then
    log "prepare_stderr_tail $(tail -c 400 "${PREP_ERR}" | tr '\n' ' ')"
  elif [[ "${#HOOK_JSON}" -le 2 ]]; then
    log "prepare_skip empty_stdin (Cursor did not pass hook JSON?)"
  else
    log "prepare_skip no_text (no transcript_path, transcripts off, quiet_hours, below min_chars, or no assistant text — check speak_summary.toml and Cursor transcript settings)"
  fi
  exit 0
fi

log "prepare_ok payload_chars=${#PAYLOAD}"

PORT="$(read_port)"
ensure_daemon "${PORT}"
PORT="$(read_port)"
post_say "${PORT}" "${PAYLOAD}"
log "post_say_done port=${PORT}"

exit 0
