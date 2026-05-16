#!/usr/bin/env bash
# Clone microsoft/VibeVoice next to Aftertone for the experiment branch.
# Does NOT modify Aftertone hooks or the Supertonic daemon.
#
#   bash scripts/setup_vibevoice.sh
#   export VIBEVOICE_REPO="$(cd ../VibeVoice && pwd)"
#
# Then install Python deps inside the VibeVoice clone (separate venv recommended):
#   cd "$VIBEVOICE_REPO" && python3 -m venv .venv && source .venv/bin/activate
#   pip install -e ".[streamingtts]"

set -euo pipefail

REPO_URL="${VIBEVOICE_REPO_URL:-https://github.com/microsoft/VibeVoice.git}"
BRANCH="${VIBEVOICE_BRANCH:-main}"
AFTERTONE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${VIBEVOICE_REPO:-${AFTERTONE_ROOT}/../VibeVoice}"

ensure_git() {
  if command -v git >/dev/null 2>&1; then
    return 0
  fi
  echo "setup_vibevoice: git is required." >&2
  exit 1
}

clone_or_update() {
  ensure_git
  if [[ -d "${TARGET}/.git" ]]; then
    echo "==> updating ${TARGET} (${BRANCH})…"
    git -C "${TARGET}" fetch origin "${BRANCH}" --depth 1 2>/dev/null || git -C "${TARGET}" fetch origin "${BRANCH}"
    git -C "${TARGET}" checkout "${BRANCH}"
    git -C "${TARGET}" pull --ff-only origin "${BRANCH}" || {
      echo "setup_vibevoice: could not fast-forward; resolve ${TARGET} manually" >&2
      exit 1
    }
  else
    echo "==> cloning ${REPO_URL} → ${TARGET}…"
    mkdir -p "$(dirname "${TARGET}")"
    git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${TARGET}"
  fi
}

clone_or_update

cat <<EOF

==> VibeVoice clone ready at: ${TARGET}

Next (use a dedicated venv — PyTorch stack, not Aftertone's ONNX venv):

  cd ${TARGET}
  python3 -m venv .venv && source .venv/bin/activate
  pip install -e ".[streamingtts]"

Smoke test:

  python demo/realtime_model_inference_from_file.py \\
    --model_path microsoft/VibeVoice-Realtime-0.5B \\
    --txt_path demo/text_examples/1p_vibevoice.txt \\
    --speaker_name Carter

Aftertone wrapper (with VibeVoice venv active):

  export VIBEVOICE_REPO=${TARGET}
  python ${AFTERTONE_ROOT}/py/vibevoice_smoke.py --text "Testing VibeVoice from Aftertone."

Docs: ${AFTERTONE_ROOT}/docs/EXPERIMENT-VIBEVOICE.md
EOF
