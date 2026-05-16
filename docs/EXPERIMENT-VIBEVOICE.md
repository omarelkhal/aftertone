# Experiment: VibeVoice backend (branch `experiment/vibevoice-realtime`)

This branch explores [Microsoft VibeVoice](https://github.com/microsoft/VibeVoice) as an alternative TTS engine for Aftertone. **`main` stays on Supertonic ONNX**; nothing here replaces the production hook path until the experiment is validated.

## What is actually available (2026)

| Model | In GitHub repo? | Fit for Aftertone spoken summaries? |
|-------|-----------------|-------------------------------------|
| **VibeVoice-TTS** (1.5B, long multi-speaker) | **Removed** from repo (Sept 2025); weights on HF marked disabled | Was long-form; not the right target today |
| **VibeVoice-Realtime-0.5B** | Yes — `pip install -e .[streamingtts]` | **Best match**: ~200–300 ms first audio, short lines, single speaker |
| **VibeVoice-ASR** | Yes | Speech-to-text, not TTS |

Official docs: [VibeVoice-Realtime-0.5B](https://github.com/microsoft/VibeVoice/blob/main/docs/vibevoice-realtime-0.5b.md) · [HF weights](https://huggingface.co/microsoft/VibeVoice-Realtime-0.5B)

Microsoft positions Realtime as **research-only** (not production); expect **PyTorch + GPU**, large downloads, and different latency/quality tradeoffs than Supertonic ONNX on CPU.

## Quick test (no Aftertone hooks yet)

1. **Bootstrap the VibeVoice clone** (sibling of this repo by default):

   ```bash
   bash scripts/setup_vibevoice.sh
   ```

2. **Use a separate venv** (recommended — conflicts with lightweight `py/` Supertonic deps):

   ```bash
   cd ../VibeVoice
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[streamingtts]"
   # CUDA: flash-attn may be required for best quality — see VibeVoice README
   ```

3. **Upstream smoke test** (writes a WAV):

   ```bash
   python demo/realtime_model_inference_from_file.py \
     --model_path microsoft/VibeVoice-Realtime-0.5B \
     --txt_path demo/text_examples/1p_vibevoice.txt \
     --speaker_name Carter
   ```

4. **Aftertone wrapper** (same inference, plays via `sounddevice` if available):

   ```bash
   export VIBEVOICE_REPO="$(cd ../VibeVoice && pwd)"
   # Aftertone py venv must NOT be required; run from VibeVoice venv OR:
   cd /path/to/VibeVoice && source .venv/bin/activate
   uv run --directory /path/to/aftertone/py python vibevoice_smoke.py \
     --text "Aftertone VibeVoice experiment. If you hear this, the backend works."
   ```

   Or from Aftertone repo after VibeVoice venv is active:

   ```bash
   export VIBEVOICE_REPO=../VibeVoice
   python py/vibevoice_smoke.py --text "Hello from the experiment branch."
   ```

## Environment variables

| Variable | Meaning |
|----------|---------|
| `VIBEVOICE_REPO` | Path to a clone of `microsoft/VibeVoice` (default `../VibeVoice`) |
| `VIBEVOICE_MODEL` | HF id or local path (default `microsoft/VibeVoice-Realtime-0.5B`) |
| `VIBEVOICE_SPEAKER` | Voice preset name (default `Carter`) — see `demo/voices/streaming_model/` |

## Roadmap (if experiment succeeds)

1. Optional `tts_backend = "vibevoice"` in `speak_summary.toml`
2. Separate daemon or subprocess pool (PyTorch model load is heavy vs ONNX daemon)
3. Map `/aftertone-voice` to VibeVoice speaker presets
4. Keep Supertonic as default on `main`

## Risks

- **VRAM / GPU**: CPU works but is slow; CUDA + `flash_attention_2` is the tested path
- **English-first** for Realtime; multilingual is experimental
- **No code paths in hooks** on this branch — only setup + smoke test
- **License**: MIT ([VibeVoice](https://github.com/microsoft/VibeVoice)); still review Microsoft usage notes
