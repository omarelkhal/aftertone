#!/usr/bin/env bash
set -euo pipefail

INSTALL_FILE="${HOME}/.cursor/hooks/aftertone-install-dir"
if [[ -f "${INSTALL_FILE}" ]]; then
  AFTERTONE_INSTALL_DIR="$(cat "${INSTALL_FILE}")"
else
  AFTERTONE_INSTALL_DIR="${AFTERTONE_INSTALL_DIR:-${AFTERTONE_REPO:-${HOME}/aftertone}}"
fi
export AFTERTONE_INSTALL_DIR

cd "${AFTERTONE_INSTALL_DIR}/py"
if [[ -x ".venv/bin/python" ]]; then
  exec .venv/bin/python -m aftertone.hook_run --stdin
fi
exec uv run python -m aftertone.hook_run --stdin
