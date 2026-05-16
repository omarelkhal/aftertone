"""Unit tests for speak_summary_prepare helpers (offline, no daemon)."""

import sys
import textwrap
from datetime import datetime, time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speak_summary_prepare import (
    _clamp,
    _code_fence_fraction,
    _demote_code_fences,
    _extract_spoken_summary,
    _parse_spoken_summary,
    _heuristic_spoken,
    _in_quiet_hours,
    _is_low_substance_sentence,
    _parse_hhmm,
    _plain_excerpt,
    _split_sentences,
    _spoken_tag_to_speakable,
    _strip_markdownish,
    _without_spoken_block,
)


class TestParseHhmm:
    def test_valid(self):
        assert _parse_hhmm("09:30") == dtime(9, 30)
        assert _parse_hhmm("23:59") == dtime(23, 59)
        assert _parse_hhmm("0:00") == dtime(0, 0)

    def test_invalid(self):
        assert _parse_hhmm("") is None
        assert _parse_hhmm("abc") is None
        assert _parse_hhmm("25:00") is None
        assert _parse_hhmm("12:60") is None
        assert _parse_hhmm("1:2") is None

    def test_whitespace(self):
        assert _parse_hhmm(" 09:30 ") == dtime(9, 30)


class TestInQuietHours:
    def _dt(self, h: int, m: int) -> datetime:
        return datetime(2024, 1, 1, h, m)

    def test_disabled(self):
        assert _in_quiet_hours(self._dt(12, 0), "") is False
        assert _in_quiet_hours(self._dt(12, 0), "none") is False
        assert _in_quiet_hours(self._dt(12, 0), "off") is False

    def test_same_day_window(self):
        spec = "09:00 - 17:00"
        assert _in_quiet_hours(self._dt(8, 0), spec) is False
        assert _in_quiet_hours(self._dt(9, 0), spec) is True
        assert _in_quiet_hours(self._dt(12, 0), spec) is True
        assert _in_quiet_hours(self._dt(16, 59), spec) is True
        assert _in_quiet_hours(self._dt(17, 0), spec) is False

    def test_overnight_window(self):
        spec = "22:00 - 08:00"
        assert _in_quiet_hours(self._dt(21, 0), spec) is False
        assert _in_quiet_hours(self._dt(22, 0), spec) is True
        assert _in_quiet_hours(self._dt(23, 59), spec) is True
        assert _in_quiet_hours(self._dt(0, 0), spec) is True
        assert _in_quiet_hours(self._dt(7, 59), spec) is True
        assert _in_quiet_hours(self._dt(8, 0), spec) is False

    def test_invalid_spec(self):
        assert _in_quiet_hours(self._dt(12, 0), "invalid") is False
        assert _in_quiet_hours(self._dt(12, 0), "99:99 - 00:00") is False


class TestExtractSpokenSummary:
    def test_found(self):
        raw = "before <spoken_summary>hello world</spoken_summary> after"
        assert _extract_spoken_summary(raw) == "hello world"

    def test_state_attribute(self):
        raw = '<spoken_summary state="blocked">Daemon is down.</spoken_summary>'
        body, state = _parse_spoken_summary(raw)
        assert body == "Daemon is down."
        assert state == "blocked"

    def test_multiline(self):
        raw = "<spoken_summary>\n  line one\n  line two\n</spoken_summary>"
        assert _extract_spoken_summary(raw) == "line one\n  line two"

    def test_not_found(self):
        assert _extract_spoken_summary("no tag here") is None

    def test_empty_tag(self):
        assert _extract_spoken_summary("<spoken_summary></spoken_summary>") is None
        assert _extract_spoken_summary("<spoken_summary>  </spoken_summary>") is None

    def test_case_insensitive(self):
        raw = "<SPOKEN_SUMMARY>test</SPOKEN_SUMMARY>"
        assert _extract_spoken_summary(raw) == "test"


class TestWithoutSpokenBlock:
    def test_removes_block(self):
        raw = "before <spoken_summary>hello</spoken_summary> after"
        result = _without_spoken_block(raw)
        assert "spoken_summary" not in result
        assert "before" in result
        assert "after" in result

    def test_no_block(self):
        raw = "just text"
        assert _without_spoken_block(raw) == "just text"


class TestStripMarkdownish:
    def test_inline_code(self):
        assert "`code`" not in _strip_markdownish("use `code` here")

    def test_links(self):
        assert _strip_markdownish("[text](http://example.com)") == "text"

    def test_headers(self):
        assert "#" not in _strip_markdownish("# Header")

    def test_bold_italic(self):
        result = _strip_markdownish("**bold** and *italic*")
        assert "**" not in result
        assert "*" not in result

    def test_urls(self):
        result = _strip_markdownish("visit http://example.com now")
        assert "http" not in result


class TestSplitSentences:
    def test_basic(self):
        sentences = _split_sentences("Hello world. How are you? Fine!")
        assert len(sentences) == 3
        assert sentences[0] == "Hello world."

    def test_empty(self):
        assert _split_sentences("") == []

    def test_single(self):
        sentences = _split_sentences("Just one sentence")
        assert len(sentences) == 1


class TestIsLowSubstanceSentence:
    def test_empty(self):
        assert _is_low_substance_sentence("") is True
        assert _is_low_substance_sentence("  ") is True

    def test_low_substance(self):
        assert _is_low_substance_sentence("Sure, I can help.") is True
        assert _is_low_substance_sentence("Here's the fix.") is True
        assert _is_low_substance_sentence("Done.") is True

    def test_has_outcome(self):
        assert _is_low_substance_sentence("I fixed the bug in the parser.") is False
        assert _is_low_substance_sentence("Added new test cases.") is False

    def test_long_sentence(self):
        long = "This is a very long sentence " * 10
        assert _is_low_substance_sentence(long) is False


class TestClamp:
    def test_no_limit(self):
        assert _clamp("hello", 0) == "hello"
        assert _clamp("hello", -1) == "hello"

    def test_under_limit(self):
        assert _clamp("hello", 10) == "hello"

    def test_over_limit(self):
        result = _clamp("hello world foo bar", 10)
        assert len(result) <= 10
        assert result.endswith("...")

    def test_strips_whitespace(self):
        assert _clamp("  hello  ", 0) == "hello"


class TestHeuristicSpoken:
    def test_basic(self):
        text = "I fixed the bug. All tests pass now."
        result = _heuristic_spoken(text, 200, 2)
        assert "fixed" in result.lower() or "tests" in result.lower()

    def test_skips_low_substance(self):
        text = "Sure. Here's the update. I fixed the parser bug."
        result = _heuristic_spoken(text, 200, 2)
        assert "fixed" in result.lower()

    def test_empty(self):
        assert _heuristic_spoken("", 200, 2) == ""


class TestCodeFenceFraction:
    def test_no_fences(self):
        assert _code_fence_fraction("hello world") == 0.0

    def test_all_code(self):
        raw = "```python\nprint('hi')\n```"
        assert _code_fence_fraction(raw) > 0.5

    def test_empty(self):
        assert _code_fence_fraction("") == 0.0


class TestDemoteCodeFences:
    def test_fences_replaced_for_plain_excerpt(self):
        raw = textwrap.dedent(
            """
            ```python
            print("not spoken verbatim")
            ```
            """
        ).strip()

        demoted = _demote_code_fences(raw)

        assert "print" not in demoted
        assert "code example" in demoted
        assert _plain_excerpt(raw, 100) == "code example"


class TestSpokenTagToSpeakable:
    def test_basic(self):
        result = _spoken_tag_to_speakable("hello world", 100)
        assert result == "hello world"

    def test_strips_markdown(self):
        result = _spoken_tag_to_speakable("**bold** and `code`", 100)
        assert "**" not in result
        assert "`" not in result

    def test_respects_cap(self):
        long_text = "word " * 100
        result = _spoken_tag_to_speakable(long_text, 50)
        assert len(result) <= 50
