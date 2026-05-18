# shellcheck shell=bash
# Resolve py/.venv Python for hook scripts (Unix bin/python vs Windows Scripts/python.exe).

aftertone_venv_python() {
  local py_dir="$1"
  if [[ -x "${py_dir}/.venv/Scripts/python.exe" ]]; then
    echo "${py_dir}/.venv/Scripts/python.exe"
    return 0
  fi
  if [[ -x "${py_dir}/.venv/bin/python" ]]; then
    echo "${py_dir}/.venv/bin/python"
    return 0
  fi
  return 1
}
