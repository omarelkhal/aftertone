"""Tests for speak_summary_config.py TOML updates."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import speak_summary_config as cfg


def _sample_toml() -> str:
    return """\
enabled = true
port = 8765
lang = "en"
speed = 1.05
mode = "queue"
voice_type = "M1"
voice_style = ""
"""


def _write_toml(tmp_path: Path, text: str) -> Path:
    hooks = tmp_path / ".cursor" / "hooks"
    hooks.mkdir(parents=True)
    p = hooks / "speak_summary.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_replace_key_preserves_comments_and_other_keys(tmp_path):
    toml_path = _write_toml(tmp_path, _sample_toml() + "# footer\n")
    text = toml_path.read_text(encoding="utf-8")
    new_text = cfg._replace_key(text, "lang", '"fr"')
    toml_path.write_text(new_text, encoding="utf-8")

    out = toml_path.read_text(encoding="utf-8")
    assert 'lang = "fr"' in out
    assert "enabled = true" in out
    assert "# footer" in out
    assert 'lang = "en"' not in out


def test_set_lang_invalid_code(tmp_path, monkeypatch):
    _write_toml(tmp_path, _sample_toml())
    monkeypatch.setattr(cfg, "_sync_spoken_rule", lambda _repo: 0)
    assert cfg.cmd_set_lang(tmp_path, "xx") == 1


def test_set_lang_valid_updates_and_syncs(tmp_path, monkeypatch):
    toml_path = _write_toml(tmp_path, _sample_toml())
    synced: list[Path] = []

    def _fake_sync(repo: Path) -> int:
        synced.append(repo)
        return 0

    monkeypatch.setattr(cfg, "_sync_spoken_rule", _fake_sync)
    assert cfg.cmd_set_lang(tmp_path, "fr") == 0
    assert synced == [tmp_path]
    assert cfg._load_cfg(toml_path)["lang"] == "fr"


def test_set_speed_rejects_out_of_range(tmp_path):
    _write_toml(tmp_path, _sample_toml())
    assert cfg.cmd_set_speed(tmp_path, "3.0") == 1


def test_set_speed_updates_toml(tmp_path):
    toml_path = _write_toml(tmp_path, _sample_toml())
    assert cfg.cmd_set_speed(tmp_path, "1.2") == 0
    assert cfg._load_cfg(toml_path)["speed"] == pytest.approx(1.2)


def test_set_mode_invalid(tmp_path):
    _write_toml(tmp_path, _sample_toml())
    assert cfg.cmd_set_mode(tmp_path, "parallel") == 1


def test_set_mode_updates_toml(tmp_path):
    toml_path = _write_toml(tmp_path, _sample_toml())
    assert cfg.cmd_set_mode(tmp_path, "interrupt") == 0
    assert cfg._load_cfg(toml_path)["mode"] == "interrupt"


def test_set_voice_preset_without_restart(tmp_path, monkeypatch, capsys):
    _write_toml(tmp_path, _sample_toml())
    monkeypatch.setattr(cfg, "_list_voice_presets", lambda _repo: ["M1", "F2"])
    assert cfg.cmd_set_voice(tmp_path, "F2", restart=False) == 0
    toml_path = tmp_path / ".cursor" / "hooks" / "speak_summary.toml"
    data = cfg._load_cfg(toml_path)
    assert data["voice_type"] == "F2"
    assert data["voice_style"] == ""
    err = capsys.readouterr().err
    assert "daemon_restart_required" in err


def test_set_voice_with_restart_calls_daemon(tmp_path, monkeypatch):
    _write_toml(tmp_path, _sample_toml())
    monkeypatch.setattr(cfg, "_list_voice_presets", lambda _repo: ["M1"])
    called: list[Path] = []
    monkeypatch.setattr(
        cfg, "_daemon_restart", lambda repo: called.append(repo) or 0
    )
    assert cfg.cmd_set_voice(tmp_path, "M1", restart=True) == 0
    assert called == [tmp_path]


def test_status_prints_fields(tmp_path, capsys):
    _write_toml(tmp_path, _sample_toml())
    assert cfg.cmd_status(tmp_path) == 0
    out = capsys.readouterr().out
    assert "lang: en" in out
    assert "enabled: on" in out
