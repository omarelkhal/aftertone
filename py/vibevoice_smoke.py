#!/usr/bin/env python3
"""
Smoke test: synthesize short text with VibeVoice-Realtime and play or save WAV.

Requires a separate VibeVoice install (PyTorch). Does not use tts_daemon or Supertonic.

  export VIBEVOICE_REPO=../VibeVoice   # clone from scripts/setup_vibevoice.sh
  python py/vibevoice_smoke.py --text "Hello from Aftertone experiment."

Run from the VibeVoice venv after: pip install -e ".[streamingtts]"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _vibevoice_root() -> Path:
    raw = os.environ.get("VIBEVOICE_REPO", "").strip()
    if raw:
        root = Path(raw).expanduser().resolve()
    else:
        root = Path(__file__).resolve().parent.parent.parent / "VibeVoice"
    infer = root / "demo" / "realtime_model_inference_from_file.py"
    if not infer.is_file():
        raise SystemExit(
            f"VibeVoice not found at {root}\n"
            "Run: bash scripts/setup_vibevoice.sh\n"
            "Then: cd ../VibeVoice && pip install -e '.[streamingtts]'"
        )
    return root


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--text", required=True, help="Text to synthesize")
    p.add_argument(
        "--model",
        default=os.environ.get("VIBEVOICE_MODEL", "microsoft/VibeVoice-Realtime-0.5B"),
    )
    p.add_argument(
        "--speaker",
        default=os.environ.get("VIBEVOICE_SPEAKER", "Carter"),
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="WAV path (default: tempfile under cwd)",
    )
    p.add_argument(
        "--play",
        action="store_true",
        default=True,
        help="Play WAV after generation (default: on)",
    )
    p.add_argument("--no-play", action="store_false", dest="play")
    args = p.parse_args()

    vv = _vibevoice_root()
    script = vv / "demo" / "realtime_model_inference_from_file.py"

    with tempfile.TemporaryDirectory(prefix="aftertone-vv-") as tmp:
        tmp_path = Path(tmp)
        txt = tmp_path / "aftertone_smoke.txt"
        txt.write_text(args.text.strip() + "\n", encoding="utf-8")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        cmd = [
            sys.executable,
            str(script),
            "--model_path",
            args.model,
            "--txt_path",
            str(txt),
            "--speaker_name",
            args.speaker,
            "--output_dir",
            str(out_dir),
        ]
        print("Running:", " ".join(cmd), flush=True)
        subprocess.run(cmd, cwd=str(vv), check=True)

        wavs = sorted(out_dir.glob("*.wav"))
        if not wavs:
            print("No WAV produced.", file=sys.stderr)
            return 1
        src = wavs[0]
        dest = args.output or Path.cwd() / "vibevoice_smoke.wav"
        dest.write_bytes(src.read_bytes())
        print(f"Wrote {dest}")

        if args.play:
            try:
                import sounddevice as sd
                import soundfile as sf

                data, rate = sf.read(dest, dtype="float32")
                sd.play(data, rate)
                sd.wait()
            except ImportError:
                print("Install sounddevice + soundfile in this venv to --play", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
