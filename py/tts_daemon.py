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
    wait: bool = False
    trace_id: str | None = None
    hook_t0_ms: int | None = None  # wall ms when Cursor hook process started
    enqueued_at_ms: int | None = None
    done: threading.Event = field(default_factory=threading.Event)
    metrics: dict[str, Any] = field(default_factory=dict)


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

    def queue_depth(self) -> int:
        return self._q.qsize()

    def enqueue(self, job: SayJob) -> None:
        if job.mode == "interrupt":
            _stop_playback(self.backend)
            _drain_queue(self._q)
        job.enqueued_at_ms = int(time.time() * 1000)
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
            synth_ms = 0
            play_ms = 0
            first_audio_ms: int | None = None
            first_sound_since_hook_ms: int | None = None
            queue_ms: int | None = None
            if job.enqueued_at_ms is not None:
                queue_ms = int(time.time() * 1000) - job.enqueued_at_ms
            self._log_job_step(job, "worker_dequeue", queue_ms=queue_ms)
            try:
                lang = ((job.lang or "").strip() or self.lang).strip()
                wav, dur_onnx = self.tts(
                    text, lang, self.style, job.total_step, job.speed
                )
                synth_ms = int((time.perf_counter() - t0) * 1000)
                self._log_job_step(job, "worker_synth_done", synth_ms=synth_ms)
                n = int(self.sample_rate * float(dur_onnx[0].item()))
                audio = np.asarray(wav[0, :n], dtype=np.float32)
                t_before_play = time.perf_counter()
                first_audio_ms = int((t_before_play - t0) * 1000)
                if job.hook_t0_ms:
                    first_sound_since_hook_ms = (
                        int(time.time() * 1000) - job.hook_t0_ms
                    )
                self._log_job_step(
                    job,
                    "worker_playback_start",
                    worker_ms=first_audio_ms,
                    first_sound_since_hook_ms=first_sound_since_hook_ms,
                )
                t_play = time.perf_counter()
                play_audio_blocking(audio, self.sample_rate, self.backend)
                play_ms = int((time.perf_counter() - t_play) * 1000)
            except Exception as e:
                print(f"[tts_daemon] synth/play error: {e}", flush=True)
                took_ms = int((time.perf_counter() - t0) * 1000)
                job.metrics = {
                    "error": str(e),
                    "took_ms": took_ms,
                    "synth_ms": synth_ms or None,
                    "play_ms": play_ms or None,
                    "first_audio_ms": first_audio_ms,
                    "total_step": job.total_step,
                }
                if job.wait:
                    job.done.set()
                continue
            took_ms = int((time.perf_counter() - t0) * 1000)
            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "job_id": job.job_id,
                "trace_id": job.trace_id,
                "generation_id": job.generation_id,
                "conversation_id": job.conversation_id,
                "text": text[:500],
                "took_ms": took_ms,
                "synth_ms": synth_ms,
                "play_ms": play_ms,
                "first_audio_ms": first_audio_ms,
                "first_sound_since_hook_ms": first_sound_since_hook_ms,
                "queue_ms": queue_ms,
                "total_step": job.total_step,
            }
            log_path = _spoken_log_path(self.repo_root)
            _append_jsonl(log_path, record)
            self._log_latency_summary(
                job,
                first_sound_since_hook_ms=first_sound_since_hook_ms,
                synth_ms=synth_ms,
                queue_ms=queue_ms,
                play_ms=play_ms,
                took_ms=took_ms,
            )
            if job.trace_id and job.hook_t0_ms:
                try:
                    from aftertone.pipeline_trace import PipelineTracer

                    ptr = PipelineTracer(
                        self.repo_root, job.trace_id, job.hook_t0_ms
                    )
                    ptr.finish_sound(
                        job_id=job.job_id,
                        first_sound_since_hook_ms=first_sound_since_hook_ms,
                        synth_ms=synth_ms,
                        queue_ms=queue_ms,
                        play_ms=play_ms,
                        worker_took_ms=took_ms,
                    )
                except Exception:
                    pass
            job.metrics = {
                k: record[k]
                for k in (
                    "took_ms",
                    "synth_ms",
                    "play_ms",
                    "first_audio_ms",
                    "total_step",
                )
            }
            if job.wait:
                job.done.set()

    def providers(self) -> list[str]:
        try:
            return list(self.tts.dp_ort.get_providers())
        except Exception:
            return []

    def _log_job_step(self, job: SayJob, step: str, **fields: Any) -> None:
        try:
            from aftertone.timing import log_latency

            log_latency(
                self.repo_root,
                step,
                trace_id=job.trace_id,
                job_id=job.job_id,
                hook_t0_ms=job.hook_t0_ms,
                **fields,
            )
        except Exception:
            pass

    def _log_latency_summary(
        self,
        job: SayJob,
        *,
        first_sound_since_hook_ms: int | None,
        synth_ms: int,
        queue_ms: int | None,
        play_ms: int,
        took_ms: int,
    ) -> None:
        try:
            from aftertone.timing import log_latency_summary

            log_latency_summary(
                self.repo_root,
                trace_id=job.trace_id,
                job_id=job.job_id,
                hook_t0_ms=job.hook_t0_ms,
                first_sound_ms=first_sound_since_hook_ms,
                synth_ms=synth_ms,
                queue_ms=queue_ms,
                play_ms=play_ms,
                worker_took_ms=took_ms,
            )
        except Exception:
            pass


def _hook_log(repo_root: str, msg: str) -> None:
    log_dir = os.path.join(repo_root, ".cursor", "hooks", "state")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "speak_summary-hook.log")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def _say_job_from_payload(body: dict[str, Any]) -> SayJob:
    total_step = int(body.get("totalStep", body.get("total_step", 8)))
    speed = float(body.get("speed", 1.0))
    raw_lang = body.get("lang") or body.get("language")
    job_lang = (
        str(raw_lang).strip()
        if isinstance(raw_lang, str) and str(raw_lang).strip()
        else None
    )
    mode = str(body.get("mode", "queue")).lower()
    if mode not in ("queue", "interrupt"):
        mode = "queue"
    return SayJob(
        text=str(body.get("text", "") or "").strip(),
        total_step=total_step,
        speed=speed,
        mode=mode,
        generation_id=body.get("generation_id") or body.get("generationId"),
        conversation_id=body.get("conversation_id") or body.get("conversationId"),
        lang=job_lang,
        wait=bool(body.get("wait")),
    )


def make_handler(worker: TTSWorker, port: int, repo_root: str):
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
            if self.path == "/hook" or self.path.startswith("/hook?"):
                t0 = time.perf_counter()
                trace_id = (self.headers.get("X-Aftertone-Trace") or "").strip() or None
                hook_t0_raw = (self.headers.get("X-Aftertone-Hook-T0-Ms") or "").strip()
                hook_t0_ms: int | None = None
                if hook_t0_raw.isdigit():
                    hook_t0_ms = int(hook_t0_raw)
                content_len = int(self.headers.get("Content-Length", "0") or 0)

                def _lat(step: str, **kw: object) -> None:
                    try:
                        from aftertone.timing import log_latency

                        log_latency(
                            repo_root,
                            step,
                            trace_id=trace_id,
                            hook_t0_ms=hook_t0_ms,
                            **kw,
                        )
                    except Exception:
                        pass

                _lat("daemon_http_in", content_length=content_len)
                raw_hook = self._read_json()
                _lat("daemon_body_read", read_ms=int((time.perf_counter() - t0) * 1000))
                if raw_hook is None:
                    self._json(400, {"error": "invalid_json"})
                    return
                hook_bytes = int(self.headers.get("Content-Length", "0") or 0)
                _hook_log(
                    repo_root,
                    f"hook_invoked hook_json_bytes={hook_bytes} via=daemon_hook "
                    f"trace={trace_id or '-'}",
                )
                from pathlib import Path

                from aftertone.config import load_config
                from aftertone.prepare import prepare_payload

                cfg = load_config(Path(repo_root))
                out = prepare_payload(raw_hook, cfg, Path(repo_root))
                prepare_ms = int((time.perf_counter() - t0) * 1000)
                if out is None:
                    reason = str(raw_hook.get("_aftertone_skip_reason") or "unknown")
                    try:
                        from aftertone.sessions import hook_adapter, hook_session_id

                        adapter = hook_adapter(raw_hook)
                        sid = hook_session_id(raw_hook, adapter) or "-"
                    except Exception:
                        adapter = "-"
                        sid = "-"
                    _hook_log(
                        repo_root,
                        f"prepare_skip reason={reason} adapter={adapter} session_id={sid}",
                    )
                    self._json(200, {"skipped": True})
                    return
                payload_chars = len(out.get("text", "") or "")
                _hook_log(repo_root, f"prepare_ok payload_chars={payload_chars}")
                job = _say_job_from_payload(out)
                job.trace_id = trace_id
                job.hook_t0_ms = hook_t0_ms
                _lat(
                    "daemon_prepare_done",
                    job_id=job.job_id,
                    prepare_ms=prepare_ms,
                    payload_chars=payload_chars,
                )
                worker.enqueue(job)
                _lat(
                    "daemon_enqueued",
                    job_id=job.job_id,
                    queue_depth=worker.queue_depth(),
                )
                _lat("daemon_http_response", job_id=job.job_id)
                wall_ms = int((time.perf_counter() - t0) * 1000)
                _hook_log(
                    repo_root,
                    f"hook_metrics prepare_ms={prepare_ms} http=202 "
                    f"payload_chars={payload_chars} hook_wall_ms={wall_ms} "
                    f"total_step={job.total_step}",
                )
                _hook_log(repo_root, f"post_say_done port={port} via=daemon_hook")
                self._json(202, {"id": job.job_id, "queuedAt": datetime.now(timezone.utc).isoformat()})
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
            job = _say_job_from_payload({**body, "text": text})
            worker.enqueue(job)
            if job.wait:
                if not job.done.wait(timeout=120.0):
                    self._json(504, {"error": "timeout", "id": job.job_id})
                    return
                if job.metrics.get("error"):
                    self._json(500, {"id": job.job_id, **job.metrics})
                    return
                self._json(200, {"id": job.job_id, **job.metrics})
                return
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
    handler = make_handler(worker, args.port, repo_root)
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
