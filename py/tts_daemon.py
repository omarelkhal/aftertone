"""
Long-running HTTP TTS daemon for Cursor stop-hook integration.

Loads Supertonic ONNX once, accepts POST /say with short text, synthesizes and
plays on a single worker thread. Logs spoken lines to
<repo>/.cursor/hooks/state/spoken/YYYY-MM-DD.jsonl.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import numpy as np

from helper import load_text_to_speech, load_voice_style
from tts_io import play_audio_blocking, resolve_playback


@dataclass
class SayJob:
    text: str
    total_step: int
    speed: float
    mode: str  # "queue" | "interrupt"
    generation_id: str | None = None
    conversation_id: str | None = None
    lang: str | None = None  # None => use worker default from daemon startup
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _spoken_log_path(root: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    d = os.path.join(root, ".cursor", "hooks", "state", "spoken")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{day}.jsonl")


def _append_jsonl(path: str, obj: dict[str, Any]) -> None:
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def _drain_queue(q: queue.Queue[SayJob | None]) -> None:
    while True:
        try:
            q.get_nowait()
        except queue.Empty:
            break


def _stop_playback(backend: str) -> None:
    if backend != "sounddevice":
        return
    try:
        import sounddevice as sd

        sd.stop()
    except Exception:
        pass


class TTSWorker:
    def __init__(
        self,
        onnx_dir: str,
        voice_style: str,
        lang: str,
        use_gpu: bool,
        repo_root: str,
    ) -> None:
        self.onnx_dir = onnx_dir
        self.voice_style = voice_style
        self.lang = lang
        self.use_gpu = use_gpu
        self.repo_root = repo_root
        self.backend = resolve_playback()
        if not self.backend:
            raise RuntimeError(
                "No audio output: install PortAudio + sounddevice, or ensure `aplay` exists."
            )
        self.tts = load_text_to_speech(onnx_dir, use_gpu=use_gpu)
        self.style = load_voice_style([voice_style], verbose=True)
        self.sample_rate = int(self.tts.sample_rate)
        self._q: queue.Queue[SayJob | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop = threading.Event()

    def start(self) -> None:
        self._thread.start()

    def enqueue(self, job: SayJob) -> None:
        if job.mode == "interrupt":
            _stop_playback(self.backend)
            _drain_queue(self._q)
        self._q.put(job)

    def shutdown(self) -> None:
        self._q.put(None)

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while True:
            job = self._q.get()
            if job is None:
                break
            text = (job.text or "").strip()
            if not text:
                continue
            t0 = time.perf_counter()
            try:
                lang = ((job.lang or "").strip() or self.lang).strip()
                wav, dur = self.tts(
                    text, lang, self.style, job.total_step, job.speed
                )
                n = int(self.sample_rate * float(dur[0].item()))
                audio = np.asarray(wav[0, :n], dtype=np.float32)
                play_audio_blocking(audio, self.sample_rate, self.backend)
            except Exception as e:
                print(f"[tts_daemon] synth/play error: {e}", flush=True)
                continue
            took_ms = int((time.perf_counter() - t0) * 1000)
            log_path = _spoken_log_path(self.repo_root)
            _append_jsonl(
                log_path,
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "job_id": job.job_id,
                    "generation_id": job.generation_id,
                    "conversation_id": job.conversation_id,
                    "text": text[:500],
                    "took_ms": took_ms,
                },
            )

    def providers(self) -> list[str]:
        try:
            return list(self.tts.dp_ort.get_providers())
        except Exception:
            return []


def make_handler(worker: TTSWorker, port: int):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            return

        def _json(self, code: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json(self) -> dict[str, Any] | None:
            n = int(self.headers.get("Content-Length", "0") or 0)
            if n <= 0:
                return {}
            raw = self.rfile.read(n)
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return None

        def do_GET(self) -> None:
            if self.path == "/healthz" or self.path.startswith("/healthz?"):
                self._json(
                    200,
                    {
                        "ready": True,
                        "providers": worker.providers(),
                        "voice": worker.voice_style,
                        "port": port,
                        "backend": worker.backend,
                    },
                )
                return
            self.send_error(404)

        def do_POST(self) -> None:
            if self.path == "/shutdown":
                worker.shutdown()
                self._json(202, {"status": "shutting_down"})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if self.path != "/say":
                self.send_error(404)
                return
            body = self._read_json()
            if body is None:
                self._json(400, {"error": "invalid_json"})
                return
            text = str(body.get("text", "") or "").strip()
            if not text:
                self._json(400, {"error": "missing_text"})
                return
            total_step = int(body.get("totalStep", body.get("total_step", 4)))
            speed = float(body.get("speed", 1.05))
            raw_lang = body.get("lang") or body.get("language")
            job_lang = (
                str(raw_lang).strip()
                if isinstance(raw_lang, str) and str(raw_lang).strip()
                else None
            )
            mode = str(body.get("mode", "queue")).lower()
            if mode not in ("queue", "interrupt"):
                mode = "queue"
            job = SayJob(
                text=text,
                total_step=total_step,
                speed=speed,
                mode=mode,
                generation_id=body.get("generation_id") or body.get("generationId"),
                conversation_id=body.get("conversation_id")
                or body.get("conversationId"),
                lang=job_lang,
            )
            worker.enqueue(job)
            self._json(
                202,
                {"id": job.job_id, "queuedAt": datetime.now(timezone.utc).isoformat()},
            )

    return H


def main() -> None:
    p = argparse.ArgumentParser(description="Supertonic TTS HTTP daemon (localhost).")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--onnx-dir", type=str, default="../assets/onnx")
    p.add_argument("--voice-style", type=str, default="../assets/voice_styles/M1.json")
    p.add_argument("--lang", type=str, default="en")
    p.add_argument("--use-gpu", action="store_true")
    p.add_argument(
        "--repo-root",
        type=str,
        default="",
        help="Workspace root for spoken/*.jsonl (default: parent of py/).",
    )
    args = p.parse_args()
    repo_root = os.path.abspath(args.repo_root or _repo_root())
    onnx_dir = os.path.abspath(
        args.onnx_dir
        if os.path.isabs(args.onnx_dir)
        else os.path.join(os.path.dirname(__file__), args.onnx_dir)
    )
    voice_style = os.path.abspath(
        args.voice_style
        if os.path.isabs(args.voice_style)
        else os.path.join(os.path.dirname(__file__), args.voice_style)
    )
    if not os.path.isdir(onnx_dir):
        print(f"ONNX dir not found: {onnx_dir}", flush=True)
        raise SystemExit(1)
    if not os.path.isfile(voice_style):
        print(f"Voice style not found: {voice_style}", flush=True)
        raise SystemExit(1)

    print(
        f"tts_daemon: loading models from {onnx_dir} (gpu={args.use_gpu})…",
        flush=True,
    )
    worker = TTSWorker(
        onnx_dir=onnx_dir,
        voice_style=voice_style,
        lang=args.lang,
        use_gpu=args.use_gpu,
        repo_root=repo_root,
    )
    worker.start()
    handler = make_handler(worker, args.port)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(
        f"tts_daemon: listening http://{args.host}:{args.port} "
        f"(backend={worker.backend})",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        worker.shutdown()
        worker.join(timeout=60.0)
        server.server_close()


if __name__ == "__main__":
    main()
