import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "speak_summary_prepare.py"


def run_prepare(tmp_path, text, config=""):
    repo = tmp_path / "repo"
    hooks = repo / ".cursor" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "speak_summary.toml").write_text(config, encoding="utf-8")

    payload = {
        "hook_event_name": "afterAgentResponse",
        "text": text,
        "generation_id": "gen-1",
        "conversation_id": "conv-1",
    }
    env = os.environ.copy()
    env["AFTERTONE_REPO"] = str(repo)
    env["SPEAK_SUMMARY_IGNORE_QUIET"] = "1"

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    return json.loads(proc.stdout)


def test_spoken_summary_strips_markdown_and_prefers_leading_sentences(tmp_path):
    out = run_prepare(
        tmp_path,
        """
Regular reply that should be ignored.
<spoken_summary>
**Fixed** the parser bug. Added `pytest` coverage. This third sentence should be capped away.
</spoken_summary>
""",
        "spoken_summary_max_chars = 52\n",
    )

    assert out["text"] == "Fixed the parser bug. Added coverage."
    assert out["generation_id"] == "gen-1"
    assert out["conversation_id"] == "conv-1"


def test_heuristic_skips_low_substance_opener(tmp_path):
    out = run_prepare(
        tmp_path,
        "Sure, I can help. Added tests for the summary picker. They cover limits.",
        "heuristic_max_sentences = 1\n",
    )

    assert out["text"] == "Added tests for the summary picker."


def test_code_heavy_reply_uses_code_heavy_sentence_limit_and_demotes_fences(tmp_path):
    out = run_prepare(
        tmp_path,
        """
```python
for i in range(100):
    print(i)
```
Implemented the fix for fenced-code replies. Added regression tests. Updated docs.
""",
        "heuristic_code_fence_fraction = 0.05\nheuristic_max_sentences = 3\nheuristic_max_sentences_code_heavy = 1\n",
    )

    assert out["text"] == "Implemented the fix for fenced-code replies."


def test_heuristic_max_chars_clamps_long_sentence(tmp_path):
    out = run_prepare(
        tmp_path,
        "Implemented a very long spoken summary sentence that should be shortened before it reaches the daemon.",
        "heuristic_max_chars = 48\n",
    )

    assert out["text"] == "Implemented a very long spoken summary..."
    assert len(out["text"]) <= 48


def test_only_speak_spoken_summary_suppresses_heuristic_fallback(tmp_path):
    out = run_prepare(
        tmp_path,
        "Implemented the fix, but no explicit spoken summary tag is present.",
        "only_speak_spoken_summary = true\n",
    )

    assert out == {}
