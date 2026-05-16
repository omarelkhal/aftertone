#!/usr/bin/env python3
"""A/B expression-tag check: saves WAVs and optionally plays via tts_daemon."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import wave
from array import array
from pathlib import Path

import numpy as np

from helper import load_text_to_speech, load_voice_style


def _save_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    pcm = (np.asarray(audio, dtype=np.float32) * 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _post_say(port: int, text: str, *, total_step: int, mode: str) -> None:
    body = json.dumps(
        {"text": text, "mode": mode, "lang": "en", "total_step": total_step}
    ).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/say",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=Path("/tmp/aftertone_expr_test"))
    parser.add_argument("--voice", default="F4")
    parser.add_argument("--total-step", type=int, default=12)
    parser.add_argument("--play", action="store_true", help="Queue short samples on daemon")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    onnx = args.repo_root / "assets" / "onnx"
    voice = args.repo_root / "assets" / "voice_styles" / f"{args.voice}.json"
    if not onnx.is_dir() or not voice.is_file():
        print("Missing assets; run scripts/bootstrap.sh from repo root.", file=sys.stderr)
        return 1

    from helper import load_text_processor

    tp = load_text_processor(str(onnx))
    samples = [
        ("01_plain", "Wow."),
        ("02_sigh_only", "<sigh>"),
        ("03_sigh_wow", "<sigh> Wow."),
        ("04_laugh_end", "That worked <laugh>"),
    ]
    print("Preprocess check:")
    for _, text in samples:
        print(f"  {text!r} -> {tp._preprocess_text(text, 'en')!r}")

    tts = load_text_to_speech(str(onnx), use_gpu=False)
    style = load_voice_style([str(voice)])
    sr = int(tts.sample_rate)

    print(f"\nWriting WAVs to {args.out} (total_step={args.total_step}):")
    for name, text in samples:
        wav, dur = tts(text, "en", style, args.total_step, 1.0)
        n = int(sr * float(dur[0].item()))
        audio = np.asarray(wav[0, :n], dtype=np.float32)
        path = args.out / f"{name}.wav"
        _save_wav(path, audio, sr)
        print(f"  {path.name}  dur={len(audio)/sr:.2f}s")

    if args.play:
        print("\nPlaying on daemon (interrupt, ~4s apart). Restart daemon if you just updated helper.py.")
        for name, text in samples:
            print(f"  >> {name}: {text!r}")
            try:
                _post_say(args.port, text, total_step=args.total_step, mode="interrupt")
            except urllib.error.URLError as e:
                print(f"daemon POST failed: {e}", file=sys.stderr)
                return 1
            time.sleep(4)

    print("\nListen to 02_sigh_only vs 01_plain — clearest contrast.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
