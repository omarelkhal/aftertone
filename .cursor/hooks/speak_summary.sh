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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=resolve_aftertone_repo.sh
source "${SCRIPT_DIR}/resolve_aftertone_repo.sh"
# shellcheck source=venv_python.sh
source "${SCRIPT_DIR}/venv_python.sh"
REPO=""
if ! resolve_aftertone_repo "${SCRIPT_DIR}"; then
  mkdir -p "${SCRIPT_DIR}/state"
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") speak_summary: could not find Aftertone install (set AFTERTONE_INSTALL_DIR or run install.sh --global)" >>"${SCRIPT_DIR}/state/speak_summary-hook.log" || true
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

# Do not store hook JSON in a bash variable — backticks, $, and quotes corrupt the payload.
HOOK_STDIN="$(mktemp "${STATE_DIR}/hook_stdin.XXXXXX.json")"
cat >"${HOOK_STDIN}" || true
VENV_PY=""
if VENV_PY="$(aftertone_venv_python "${PY}")"; then
  "${VENV_PY}" "${PY}/hook_stdin_normalize.py" "${HOOK_STDIN}" 2>/dev/null || true
fi
HOOK_BYTES="$(wc -c <"${HOOK_STDIN}" | tr -d ' \n\r')"
if VENV_PY="$(aftertone_venv_python "${PY}")"; then
  <"${HOOK_STDIN}" "${VENV_PY}" "${PY}/hook_payload_trace.py" "${STATE_DIR}/hook_payload_trace.jsonl" 2>/dev/null || true
fi
log "hook_invoked hook_json_bytes=${HOOK_BYTES}"

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
  local vpy=""
  if vpy="$(aftertone_venv_python "${PY}")"; then
    <"${HOOK_STDIN}" "${vpy}" "${PY}/speak_summary_prepare.py" 2>>"${PREP_ERR}"
    return $?
  fi
  if command -v uv >/dev/null 2>&1; then
    <"${HOOK_STDIN}" bash -c "cd \"${PY}\" && uv run python speak_summary_prepare.py" 2>>"${PREP_ERR}"
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    <"${HOOK_STDIN}" env PYTHONPATH="${PY}" python3 "${PY}/speak_summary_prepare.py" 2>>"${PREP_ERR}"
    return $?
  fi
  log "prepare_skip no_python venv_missing=${PY}/.venv uv_missing=1"
  echo '{}'
  return 1
}

ensure_daemon() {
  local port="$1"
  if curl -fsS -m 0.35 "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1; then
    return 0
  fi
  log "daemon_bootstrap port=${port}"
  local vpy=""
  if vpy="$(aftertone_venv_python "${PY}")"; then
    "${vpy}" "${PY}/tts_daemon_ctl.py" start --repo-root "${REPO}" >>"${STATE_DIR}/tts-daemon-bootstrap.log" 2>&1 || true
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
  local tmp vpy http_code
  tmp="$(mktemp "${STATE_DIR}/say_payload.XXXXXX.json")"
  printf '%s' "${payload}" >"${tmp}"
  if [[ -f "${PY}/post_say_hook.py" ]] && vpy="$(aftertone_venv_python "${PY}")"; then
    http_code="$("${vpy}" "${PY}/post_say_hook.py" "${port}" "${tmp}" 2>/dev/null || true)"
    if [[ "${http_code}" == "202" ]] || [[ "${http_code}" == "200" ]]; then
      rm -f "${tmp}"
      return 0
    fi
  elif command -v curl >/dev/null 2>&1; then
    if curl -fsS -m 30 -X POST "http://127.0.0.1:${port}/say" \
      -H "Content-Type: application/json" \
      --data-binary @"${tmp}" >/dev/null 2>&1; then
      rm -f "${tmp}"
      return 0
    fi
  fi
  log "post_say_failed port=${port} http=${http_code:-none}"
  rm -f "${tmp}"
  return 1
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
  elif [[ "${HOOK_BYTES:-0}" -le 2 ]]; then
    log "prepare_skip empty_stdin (Cursor did not pass hook JSON?)"
  else
    cp "${HOOK_STDIN}" "${STATE_DIR}/last-hook-skipped.json" 2>/dev/null || true
    skip_detail=""
    if vpy="$(aftertone_venv_python "${PY}")"; then
      skip_detail="$("${vpy}" "${PY}/hook_skip_diag.py" "${HOOK_STDIN}" 2>/dev/null || true)"
    fi
    if [[ -n "${skip_detail}" ]]; then
      log "prepare_skip no_text ${skip_detail}"
    else
      log "prepare_skip no_text (check speak_summary.toml: enabled, only_speak_spoken_summary, quiet_hours)"
    fi
  fi
  rm -f "${HOOK_STDIN}"
  exit 0
fi

log "prepare_ok payload_chars=${#PAYLOAD}"

PORT="$(read_port)"
ensure_daemon "${PORT}"
PORT="$(read_port)"
if post_say "${PORT}" "${PAYLOAD}"; then
  log "post_say_done port=${PORT}"
else
  log "post_say_failed_after_prepare port=${PORT}"
fi

rm -f "${HOOK_STDIN}"
exit 0
