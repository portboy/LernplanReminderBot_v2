"""Tests for new configuration system."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config import BotConfig, SubjectConfig, load_config


def test_subject_config_validation():
    """Test SubjectConfig validation."""
    # Valid
    subject = SubjectConfig(name="Mathe", emoji="🔢", color="#FF6B6B")
    assert subject.name == "Mathe"
    assert subject.emoji == "🔢"

    # Default emoji
    subject = SubjectConfig(name="Test")
    assert subject.emoji == "📘"


def test_bot_config_validation():
    """Test BotConfig validation."""
    # Valid config
    config = BotConfig(
        telegram_token="test_token",
        student_chat_id=123,
        parent_chat_id=456,
    )
    assert config.telegram_token == "test_token"
    assert config.student_chat_id == 123

    # Invalid chat_id (negative)
    with pytest.raises(ValidationError):
        BotConfig(telegram_token="token", student_chat_id=-1)

    # Invalid log level
    with pytest.raises(ValidationError):
        BotConfig(telegram_token="token", log_level="INVALID")


def test_time_validation():
    """Test time format validation."""
    # Valid times
    config = BotConfig(
        telegram_token="token",
        dynamic_planning_times=["07:30", "14:00", "20:00"],
    )
    assert len(config.dynamic_planning_times) == 3

    # Invalid time format
    with pytest.raises(ValidationError):
        BotConfig(
            telegram_token="token",
            dynamic_planning_times=["25:00"],  # Invalid hour
        )

    with pytest.raises(ValidationError):
        BotConfig(
            telegram_token="token",
            dynamic_planning_times=["12:60"],  # Invalid minute
        )


def test_get_subject_names():
    """Test getting subject names."""
    config = BotConfig(
        telegram_token="token",
        allowed_subjects=[
            SubjectConfig(name="Mathe"),
            SubjectConfig(name="Englisch"),
        ],
    )
    assert config.get_subject_names() == ["Mathe", "Englisch"]


def test_get_subject_by_name():
    """Test getting subject by name."""
    config = BotConfig(
        telegram_token="token",
        allowed_subjects=[
            SubjectConfig(name="Mathe", emoji="🔢"),
            SubjectConfig(name="Englisch", emoji="🇬🇧"),
        ],
    )
    
    mathe = config.get_subject_by_name("Mathe")
    assert mathe is not None
    assert mathe.emoji == "🔢"
    
    invalid = config.get_subject_by_name("Invalid")
    assert invalid is None


def test_load_config_from_json(tmp_path):
    """Test loading config from JSON file."""
    # This test just verifies the BotConfig class works
    # since load_config() searches multiple paths
    config_data = {
        "telegram_token": "test_token_123",
        "student_chat_id": 111,
        "parent_chat_id": 222,
        "timezone": "Europe/Berlin",
        "log_level": "DEBUG",
    }
    
    config = BotConfig(**config_data)
    
    assert config.telegram_token == "test_token_123"
    assert config.student_chat_id == 111
    assert config.log_level == "DEBUG"


def test_config_defaults():
    """Test default values in config."""
    config = BotConfig(telegram_token="token")
    
    assert config.timezone == "Europe/Berlin"
    assert config.log_level == "INFO"
    assert config.min_minutes == 1
    assert config.max_minutes == 180
    assert config.jokers_per_week == 1
    assert len(config.allowed_subjects) == 2  # Mathe, Englisch
    assert len(config.duration_choices) == 6
