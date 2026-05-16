import io
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import speak_summary_prepare as prepare


def _run_prepare(monkeypatch, capsys, tmp_path, text, config=""):
    cfg_dir = tmp_path / ".cursor" / "hooks"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "speak_summary.toml").write_text(config, encoding="utf-8")

    monkeypatch.setenv("AFTERTONE_REPO", str(tmp_path))
    monkeypatch.setenv("SPEAK_SUMMARY_IGNORE_QUIET", "1")
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "hook_event_name": "afterAgentResponse",
                    "text": text,
                    "generation_id": "test-generation",
                    "conversation_id": "test-conversation",
                }
            )
        ),
    )

    prepare.main()
    return json.loads(capsys.readouterr().out)


def test_spoken_summary_uses_leading_sentences_with_cap(monkeypatch, capsys, tmp_path):
    result = _run_prepare(
        monkeypatch,
        capsys,
        tmp_path,
        (
            "<spoken_summary>First sentence fits. "
            "Second sentence should not be read aloud.</spoken_summary>"
            "The untagged body should not be used."
        ),
        "max_chars = 200\nspoken_summary_max_chars = 30\n",
    )

    assert result["text"] == "First sentence fits."
    assert result["generation_id"] == "test-generation"
    assert result["conversation_id"] == "test-conversation"


def test_heuristic_skips_low_substance_openers(monkeypatch, capsys, tmp_path):
    result = _run_prepare(
        monkeypatch,
        capsys,
        tmp_path,
        (
            "Sure, I can help. "
            "Updated the config parser to ignore blank lines. "
            "Added tests for edge cases. "
            "Left docs unchanged."
        ),
        "max_chars = 500\nheuristic_max_chars = 200\nheuristic_max_sentences = 2\n",
    )

    assert result["text"] == (
        "Updated the config parser to ignore blank lines. "
        "Added tests for edge cases."
    )


def test_code_fences_are_replaced_for_plain_excerpt():
    raw = textwrap.dedent(
        """
        ```python
        print("not spoken verbatim")
        ```
        """
    ).strip()

    demoted = prepare._demote_code_fences(raw)

    assert "print" not in demoted
    assert "code example" in demoted
    assert prepare._plain_excerpt(raw, 100) == "code example"


def test_heuristic_character_cap_clamps_long_sentence(monkeypatch, capsys, tmp_path):
    result = _run_prepare(
        monkeypatch,
        capsys,
        tmp_path,
        (
            "Updated the hook summary output to include enough detail for "
            "maintainers before it reaches the daemon. Added regression tests."
        ),
        "max_chars = 500\nheuristic_max_chars = 48\nheuristic_max_sentences = 2\n",
    )

    assert len(result["text"]) <= 48
    assert result["text"].endswith("...")
    assert "Added regression tests" not in result["text"]
