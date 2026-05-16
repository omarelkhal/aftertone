import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import speak_summary_prepare as prep


def test_heuristic_spoken_skips_low_substance_openers():
    raw = (
        "Sure, I can help with that. "
        "Added parser coverage for timestamp variants. "
        "Ran pytest successfully."
    )

    spoken = prep._heuristic_spoken(raw, max_chars=160, max_sentences=2)

    assert spoken == (
        "Added parser coverage for timestamp variants. Ran pytest successfully."
    )


def test_code_fence_fallback_still_returns_speakable_text():
    raw = "```python\nprint('hello')\n```"

    assert prep._code_fence_fraction(raw) > 0.5
    assert prep._plain_excerpt(raw, max_chars=80) == "code example"


def test_spoken_summary_tag_uses_leading_sentences_with_cap():
    raw = (
        "First sentence fits. "
        "Second sentence should not be included because it exceeds the cap."
    )

    spoken = prep._spoken_tag_to_speakable(raw, cap=28)

    assert spoken == "First sentence fits."


def test_plain_excerpt_clamps_to_word_boundary():
    raw = "Updated the daemon startup path and verified the hook output."

    spoken = prep._plain_excerpt(raw, max_chars=35)

    assert spoken == "Updated the daemon startup path..."
    assert len(spoken) <= 35
