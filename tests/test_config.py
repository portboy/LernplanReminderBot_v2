"""Tests for BotConfig validation and load_config."""

import json
import os

import pytest
from core.config import BotConfig, SubjectConfig, load_config


def test_minimal_valid_config():
    """Config works with just token."""
    cfg = BotConfig(telegram_token="abc:123")
    assert cfg.telegram_token == "abc:123"
    assert cfg.timezone == "Europe/Berlin"
    assert cfg.max_reminder_times == 3


def test_subject_config_defaults():
    s = SubjectConfig(name="Bio")
    assert s.emoji == "📘"
    assert s.color == "#000000"


def test_log_level_uppercased():
    cfg = BotConfig(telegram_token="x", log_level="debug")
    assert cfg.log_level == "DEBUG"


def test_invalid_log_level():
    with pytest.raises(ValueError, match="Invalid log level"):
        BotConfig(telegram_token="x", log_level="TRACE")


def test_invalid_chat_id():
    with pytest.raises(ValueError, match="positive"):
        BotConfig(telegram_token="x", student_chat_id=-1)


def test_empty_token_rejected():
    with pytest.raises(ValueError):
        BotConfig(telegram_token="")


def test_invalid_time_format():
    with pytest.raises(ValueError, match="Invalid time"):
        BotConfig(telegram_token="x", dynamic_planning_times=["25:00"])


def test_get_subject_by_name():
    cfg = BotConfig(
        telegram_token="x",
        allowed_subjects=[SubjectConfig(name="Mathe", emoji="🔢")],
    )
    assert cfg.get_subject_by_name("Mathe") is not None
    assert cfg.get_subject_by_name("Physik") is None


def test_get_subject_names():
    cfg = BotConfig(
        telegram_token="x",
        allowed_subjects=[
            SubjectConfig(name="A", emoji="1"),
            SubjectConfig(name="B", emoji="2"),
        ],
    )
    assert cfg.get_subject_names() == ["A", "B"]


def test_load_config_from_json(tmp_path, monkeypatch):
    """load_config reads JSON when file exists."""
    cfg_file = tmp_path / "bot_config.json"
    cfg_file.write_text(json.dumps({"telegram_token": "from_json"}))

    monkeypatch.chdir(tmp_path)
    (tmp_path / "userconfig").mkdir()
    (tmp_path / "userconfig" / "bot_config.json").write_text(
        json.dumps({"telegram_token": "from_json"})
    )

    cfg = load_config()
    assert cfg.telegram_token == "from_json"


def test_load_config_env_override(tmp_path, monkeypatch):
    """Environment variable overrides JSON value."""
    (tmp_path / "userconfig").mkdir()
    (tmp_path / "userconfig" / "bot_config.json").write_text(
        json.dumps({"telegram_token": "from_json"})
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TELEGRAM_TOKEN", "from_env")

    cfg = load_config()
    assert cfg.telegram_token == "from_env"


def test_load_config_env_only(tmp_path, monkeypatch):
    """Config loads from env when no JSON exists."""
    monkeypatch.chdir(tmp_path)  # no userconfig/ here
    monkeypatch.setenv("TELEGRAM_TOKEN", "env_only")

    cfg = load_config()
    assert cfg.telegram_token == "env_only"
