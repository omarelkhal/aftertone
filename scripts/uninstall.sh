#!/usr/bin/env bash
# Remove a global Aftertone install on Linux (Cursor hooks + optional install tree).
#
#   curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/uninstall.sh | bash
#
# Options (pass after bash -s --):
#   --dir PATH       Install root (default: marker file, then ~/aftertone)
#   --keep-dir       Unregister ~/.cursor hooks but keep the clone and assets
#   --no-global      Skip ~/.cursor cleanup (only stop daemon / remove --dir tree)
#   --yes            Skip confirmation before deleting the install directory
#   --dry-run        Print actions without changing anything
#   -h, --help
#
# Windows uninstall: see scripts/uninstall.ps1 (irm one-liner or -File from clone).

set -euo pipefail

INSTALL_DIR=""
KEEP_DIR=0
GLOBAL_HOOKS=1
ASSUME_YES=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Aftertone uninstall (Linux) — stop daemon, remove user Cursor hooks, delete install tree.

One-liner:
  curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/uninstall.sh | bash

Keep the clone and ONNX assets (hooks only):
  curl -fsSL .../uninstall.sh | bash -s -- --keep-dir

Environment:
  AFTERTONE_INSTALL_DIR   Same as --dir
EOF
}

require_linux() {
  case "$(uname -s)" in
    Linux) ;;
    *)
      echo "uninstall: this script targets Linux only (detected: $(uname -s))." >&2
      echo "  Windows: irm https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/uninstall.ps1 | iex" >&2
      exit 1
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --keep-dir) KEEP_DIR=1; shift ;;
    --no-global) GLOBAL_HOOKS=0; shift ;;
    --yes) ASSUME_YES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "uninstall: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_linux

MARKER_REL="py/speak_summary_prepare.py"
INSTALL_DIR="${AFTERTONE_INSTALL_DIR:-${INSTALL_DIR}}"
MARKER_FILE="${HOME}/.cursor/hooks/aftertone-install-dir"

resolve_install_dir() {
  if [[ -n "${INSTALL_DIR}" ]]; then
    echo "${INSTALL_DIR}"
    return 0
  fi
  if [[ -f "${MARKER_FILE}" ]]; then
    tr -d '\n\r' <"${MARKER_FILE}"
    return 0
  fi
  echo "${HOME}/aftertone"
}

INSTALL_DIR="$(resolve_install_dir)"
if [[ -d "${INSTALL_DIR}" ]]; then
  INSTALL_DIR="$(cd "${INSTALL_DIR}" && pwd)"
fi

is_aftertone_root() {
  [[ -f "${1}/${MARKER_REL}" ]]
}

stop_daemon() {
  local root="$1"
  [[ -d "${root}/py" ]] || return 0
  echo "==> uninstall: stopping tts_daemon (if running)…"
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "would run: cd ${root}/py && uv run python tts_daemon_ctl.py stop --repo-root .."
    return 0
  fi
  if [[ -x "${root}/py/.venv/bin/python" ]]; then
    (cd "${root}/py" && "${root}/py/.venv/bin/python" tts_daemon_ctl.py stop --repo-root ..) \
      2>/dev/null || true
  elif command -v uv >/dev/null 2>&1; then
    (cd "${root}/py" && uv run python tts_daemon_ctl.py stop --repo-root ..) 2>/dev/null || true
  fi
  pkill -f "tts_daemon.py" 2>/dev/null || true
}

# curl | bash has no script path on disk; BASH_SOURCE[0] is unset under set -u.
_SCRIPT_SRC="${BASH_SOURCE[0]:-}"
if [[ -n "${_SCRIPT_SRC}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${_SCRIPT_SRC}")" && pwd)"
  REPO_FROM_SCRIPT="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
  REPO_FROM_SCRIPT=""
fi

run_uninstall_global_hooks() {
  local extra=("$@")
  local py_roots=()
  if [[ -n "${REPO_FROM_SCRIPT}" ]] && [[ -f "${REPO_FROM_SCRIPT}/py/uninstall_global_hooks.py" ]]; then
    py_roots+=("${REPO_FROM_SCRIPT}")
  fi
  if [[ -f "${INSTALL_DIR}/py/uninstall_global_hooks.py" ]] \
    && [[ "$(cd "${INSTALL_DIR}" && pwd)" != "$(cd "${REPO_FROM_SCRIPT}" && pwd)" ]]; then
    py_roots+=("${INSTALL_DIR}")
  fi
  local root
  for root in "${py_roots[@]}"; do
    if [[ -x "${root}/py/.venv/bin/python" ]]; then
      (cd "${root}/py" && "${root}/py/.venv/bin/python" uninstall_global_hooks.py "${extra[@]}")
      return 0
    fi
    if command -v uv >/dev/null 2>&1; then
      (cd "${root}/py" && uv run python uninstall_global_hooks.py "${extra[@]}")
      return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
      (cd "${root}/py" && python3 uninstall_global_hooks.py "${extra[@]}")
      return 0
    fi
  done

  if ! command -v python3 >/dev/null 2>&1; then
    return 1
  fi
  local tmp py_url
  py_url="${AFTERTONE_UNINSTALL_RAW_BASE:-https://raw.githubusercontent.com/omarelkhal/aftertone/main/py}"
  tmp="$(mktemp -d)"
  cleanup_tmp() { rm -rf "${tmp}"; }
  trap cleanup_tmp RETURN
  echo "==> uninstall: fetching hook helpers from ${py_url}…"
  if ! curl -fsSL "${py_url}/install_global_hooks.py" -o "${tmp}/install_global_hooks.py" \
    || ! curl -fsSL "${py_url}/install_global_claude_hooks.py" -o "${tmp}/install_global_claude_hooks.py" \
    || ! curl -fsSL "${py_url}/install_global_codex_hooks.py" -o "${tmp}/install_global_codex_hooks.py" \
    || ! curl -fsSL "${py_url}/uninstall_global_hooks.py" -o "${tmp}/uninstall_global_hooks.py"; then
    echo "uninstall: could not download uninstall_global_hooks.py (not on main yet? use a clone: bash scripts/uninstall.sh)" >&2
    cleanup_tmp
    trap - RETURN
    return 1
  fi
  (cd "${tmp}" && python3 uninstall_global_hooks.py "${extra[@]}")
  cleanup_tmp
  trap - RETURN
}

uninstall_global_hooks() {
  echo "==> uninstall: removing user-level Cursor hooks (~/.cursor)…"
  local flags=()
  [[ "${DRY_RUN}" == "1" ]] && flags+=(--dry-run)
  if run_uninstall_global_hooks "${flags[@]}"; then
    return 0
  fi
  echo "uninstall: could not run uninstall_global_hooks.py (need python3, uv, or an install tree)." >&2
  echo "  Remove manually: ~/.cursor/hooks/aftertone-* ~/.cursor/commands/aftertone-*" >&2
  return 1
}

remove_install_dir() {
  local root="$1"
  if [[ "${KEEP_DIR}" == "1" ]]; then
    echo "==> uninstall: keeping install directory (--keep-dir): ${root}"
    return 0
  fi
  if ! is_aftertone_root "${root}"; then
    if [[ -d "${root}" ]]; then
      echo "uninstall: ${root} is not an Aftertone install (no ${MARKER_REL}); not deleting." >&2
    else
      echo "==> uninstall: no install directory at ${root}"
    fi
    return 0
  fi

  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "would remove directory: ${root}"
    return 0
  fi

  if [[ "${ASSUME_YES}" != "1" ]]; then
    echo ""
    echo "This will permanently delete:"
    echo "  ${root}"
    echo "(including ONNX assets under assets/ — large download to restore.)"
    printf "Type 'yes' to continue: "
    read -r confirm
    if [[ "${confirm}" != "yes" ]]; then
      echo "uninstall: cancelled (install directory kept)."
      return 0
    fi
  fi

  echo "==> uninstall: removing ${root}…"
  rm -rf "${root}"
  echo "removed: ${root}"
}

main() {
  if is_aftertone_root "${INSTALL_DIR}"; then
    stop_daemon "${INSTALL_DIR}"
  fi

  if [[ "${GLOBAL_HOOKS}" == "1" ]]; then
    uninstall_global_hooks || true
  else
    echo "==> uninstall: skipping ~/.cursor (--no-global)"
  fi

  remove_install_dir "${INSTALL_DIR}"

  cat <<EOF

==> Aftertone uninstall finished.

  Mute only (re-install hooks): curl .../install.sh | bash
  Per-project speech hooks: remove afterAgentResponse from that repo's .cursor/hooks.json
  Docs: README.md § Uninstall
EOF
}

main "$@"
