#!/usr/bin/env bash
# One-line install: clone (or update) Aftertone, run bootstrap, optional daemon start.
#
#   curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash
#
# Options (also: curl ... | bash -s -- --help):
#   --dir PATH          Install/update clone here (default: ~/aftertone or $AFTERTONE_INSTALL_DIR)
#   --branch NAME       Git branch (default: main)
#   --into PATH         Copy Cursor hooks + py into another repo; symlink shared assets (legacy)
#   --global            Register user-level Cursor hooks (~/.cursor/hooks.json) — default
#   --no-global         Skip user-level hooks (project-only / manual --into)
#   --skip-assets       Skip Hugging Face model download (bootstrap SKIP_ASSETS=1)
#   --start-daemon      Start tts_daemon after bootstrap
#   --install-uv        If uv is missing, run Astral's installer (https://astral.sh/uv)
#   -h, --help

set -euo pipefail

REPO_URL="${AFTERTONE_REPO_URL:-https://github.com/omarelkhal/aftertone.git}"
BRANCH="${AFTERTONE_BRANCH:-main}"
INSTALL_DIR="${AFTERTONE_INSTALL_DIR:-${HOME}/aftertone}"
INTO=""
SKIP_ASSETS=0
START_DAEMON=0
INSTALL_UV=0
GLOBAL_HOOKS=1

usage() {
  cat <<'EOF'
Aftertone installer — clone, bootstrap (uv + ONNX assets), optional daemon.

One-liner:
  curl -fsSL https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.sh | bash

With options:
  curl -fsSL .../install.sh | bash -s -- --dir ~/aftertone --install-uv --start-daemon

Global hooks (default — TTS in every Cursor workspace):
  curl -fsSL .../install.sh | bash -s -- --install-uv --start-daemon

Legacy: copy hooks into one project:
  curl -fsSL .../install.sh | bash -s -- --no-global --into .

Environment:
  AFTERTONE_INSTALL_DIR   Same as --dir
  AFTERTONE_REPO_URL      Override git remote
  AFTERTONE_BRANCH        Same as --branch
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --into)
      INTO="$2"
      shift 2
      ;;
    --global) GLOBAL_HOOKS=1; shift ;;
    --no-global) GLOBAL_HOOKS=0; shift ;;
    --skip-assets) SKIP_ASSETS=1; shift ;;
    --start-daemon) START_DAEMON=1; shift ;;
    --install-uv) INSTALL_UV=1; shift ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "install: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

INSTALL_DIR="$(cd "${INSTALL_DIR}" 2>/dev/null && pwd || echo "${INSTALL_DIR}")"

ensure_git() {
  if command -v git >/dev/null 2>&1; then
    return 0
  fi
  echo "install: git is required. Install git, then re-run." >&2
  exit 1
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  if [[ "${INSTALL_UV}" == "1" ]]; then
    echo "==> install: uv not found; running Astral installer…"
    curl -fsSL https://astral.sh/uv/install.sh | sh
    # shellcheck disable=SC1091
    [[ -f "${HOME}/.local/bin/env" ]] && source "${HOME}/.local/bin/env"
    export PATH="${HOME}/.local/bin:${PATH}"
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "install: uv is required." >&2
    echo "  Install: https://docs.astral.sh/uv/getting-started/installation/" >&2
    echo "  Or re-run with: --install-uv" >&2
    exit 1
  fi
}

clone_or_update() {
  ensure_git
  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    echo "==> install: updating ${INSTALL_DIR} (${BRANCH})…"
    git -C "${INSTALL_DIR}" fetch origin "${BRANCH}" --depth 1 2>/dev/null || \
      git -C "${INSTALL_DIR}" fetch origin "${BRANCH}"
    git -C "${INSTALL_DIR}" checkout "${BRANCH}"
    if ! git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"; then
      echo "==> install: local changes or diverged history; resetting to origin/${BRANCH}…"
      git -C "${INSTALL_DIR}" fetch origin "${BRANCH}"
      git -C "${INSTALL_DIR}" reset --hard "origin/${BRANCH}"
      git -C "${INSTALL_DIR}" clean -fd
    fi
  else
    echo "==> install: cloning ${REPO_URL} → ${INSTALL_DIR} (${BRANCH})…"
    mkdir -p "$(dirname "${INSTALL_DIR}")"
    git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
  fi
}

run_bootstrap() {
  local root="$1"
  local env_args=()
  env_args+=(SKIP_WEB=1)
  if [[ "${SKIP_ASSETS}" == "1" ]]; then
    env_args+=(SKIP_ASSETS=1)
  fi
  echo "==> install: bootstrap (uv sync + assets)…"
  env "${env_args[@]}" bash "${root}/scripts/bootstrap.sh"
}

start_daemon() {
  local root="$1"
  echo "==> install: starting tts_daemon…"
  (cd "${root}/py" && uv run python tts_daemon_ctl.py start --repo-root ..) || {
    echo "install: daemon start failed (run manually: cd ${root}/py && uv run python tts_daemon_ctl.py start --repo-root ..)" >&2
    return 1
  }
}

enable_spoken_tts() {
  local root="$1"
  echo "==> install: enabling spoken TTS in speak_summary.toml…"
  (cd "${root}/py" && uv run python speak_summary_toggle.py on) || {
    echo "install: could not set enabled=true (use /aftertone-on in Cursor)" >&2
    return 1
  }
}

sync_spoken_summary_rule() {
  local root="$1"
  echo "==> install: syncing spoken-summary Cursor rule…"
  (cd "${root}/py" && uv run python sync_spoken_rule_lang.py) || {
    echo "install: could not sync spoken-summary.mdc" >&2
    return 1
  }
  mkdir -p "${HOME}/.cursor/rules"
  cp "${root}/.cursor/rules/spoken-summary.mdc" "${HOME}/.cursor/rules/spoken-summary.mdc"
}

install_global_hooks() {
  local root="$1"
  local vpy=""
  echo "==> install: user-level Cursor hooks (~/.cursor)…"
  if [[ -x "${root}/py/.venv/Scripts/python.exe" ]]; then
    vpy="${root}/py/.venv/Scripts/python.exe"
  elif [[ -x "${root}/py/.venv/bin/python" ]]; then
    vpy="${root}/py/.venv/bin/python"
  fi
  if [[ -n "${vpy}" ]]; then
    "${vpy}" "${root}/py/install_global_hooks.py" --install-dir "${root}"
  elif command -v uv >/dev/null 2>&1; then
    (cd "${root}/py" && uv run python install_global_hooks.py --install-dir "${root}")
  else
    echo "install: skip global hooks (no python/uv yet; re-run after: cd ${root}/py && uv sync)" >&2
    return 1
  fi
}

integrate_into() {
  local target="$1"
  local root="${INSTALL_DIR}"
  target="$(cd "${target}" && pwd)"
  echo "==> install: integrating Aftertone into ${target}…"

  mkdir -p "${target}/.cursor"
  if [[ -f "${target}/.cursor/hooks.json" ]] && ! cmp -s "${root}/.cursor/hooks.json" "${target}/.cursor/hooks.json" 2>/dev/null; then
    local bak="${target}/.cursor/hooks.json.bak.$(date +%s)"
    echo "install: backing up existing .cursor/hooks.json → ${bak}"
    cp "${target}/.cursor/hooks.json" "${bak}"
  fi

  cp "${root}/.cursor/hooks.json" "${target}/.cursor/hooks.json"
  rm -rf "${target}/.cursor/hooks" "${target}/.cursor/commands"
  cp -a "${root}/.cursor/hooks" "${target}/.cursor/hooks"
  cp -a "${root}/.cursor/commands" "${target}/.cursor/commands"
  mkdir -p "${target}/.cursor/rules"
  cp "${root}/.cursor/rules/spoken-summary.mdc" "${target}/.cursor/rules/spoken-summary.mdc"

  rm -rf "${target}/py"
  cp -a "${root}/py" "${target}/py"

  if [[ -e "${target}/assets" && ! -L "${target}/assets" ]]; then
    echo "install: ${target}/assets already exists (not replaced). Ensure onnx paths match speak_summary.toml." >&2
  else
    ln -sfn "${root}/assets" "${target}/assets"
  fi

  echo "==> install: integrated. Open ${target} in Cursor (trusted workspace)."
}

print_next_steps() {
  local root="$1"
  local global_note=""
  if [[ "${GLOBAL_HOOKS}" == "1" ]]; then
    global_note="
  Global install: spoken TTS hooks run in **any** Cursor project you open.
  Config slash commands: open ${root} in Cursor, or run CLIs with:
    AFTERTONE_INSTALL_DIR=${root} uv run --directory ${root}/py python speak_summary_config.py status"
  else
    global_note="
  Per-project: run install with --into . or open ${root} as the workspace root."
  fi
  cat <<EOF

==> Aftertone is ready at: ${root}
${global_note}

Next:
  1. Enable Hooks in Cursor Settings
  2. Trust each workspace where you want TTS (or your usual projects if global hooks are on)
  3. Daemon: cd ${root}/py && uv run python tts_daemon_ctl.py start --repo-root ..
  4. Turn on TTS: open ${root} and use /aftertone-on — or: uv run --directory ${root}/py python speak_summary_toggle.py on

Docs: ${root}/README.md  ·  hooks: ${root}/.cursor/hooks/README.md
EOF
}

main() {
  clone_or_update
  ensure_uv
  run_bootstrap "${INSTALL_DIR}"

  if [[ "${GLOBAL_HOOKS}" == "1" ]]; then
    install_global_hooks "${INSTALL_DIR}" || true
  fi

  if [[ -n "${INTO}" ]]; then
    integrate_into "${INTO}"
  fi

  if [[ "${START_DAEMON}" == "1" ]]; then
    enable_spoken_tts "${INSTALL_DIR}" || true
    sync_spoken_summary_rule "${INSTALL_DIR}" || true
    start_daemon "${INSTALL_DIR}" || true
  fi

  print_next_steps "${INSTALL_DIR}"
}

main "$@"
