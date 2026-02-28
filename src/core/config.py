"""Configuration management with JSON file support."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

LOGGER = logging.getLogger(__name__)


class SubjectConfig(BaseModel):
    """Configuration for a subject."""

    name: str
    emoji: str = "📘"
    color: str = "#000000"


class BotConfig(BaseModel):
    """Bot configuration loaded from JSON file or environment."""

    telegram_token: str = Field(..., min_length=1)
    student_chat_id: int | None = None
    parent_chat_id: int | None = None
    timezone: str = "Europe/Berlin"
    log_level: str = "INFO"
    data_dir: str = "/app/data"
    config_dir: str = "/app/userconfig"

    # Configurable subjects
    allowed_subjects: list[SubjectConfig] = Field(
        default_factory=lambda: [
            SubjectConfig(name="Mathe", emoji="🔢", color="#FF6B6B"),
            SubjectConfig(name="Englisch", emoji="🇬🇧", color="#4ECDC4"),
        ]
    )

    # Planning times
    dynamic_planning_times: list[str] = Field(
        default_factory=lambda: ["07:30", "09:00", "14:00", "16:30", "18:30", "20:30"]
    )
    duration_choices: list[int] = Field(default_factory=lambda: [15, 30, 45, 60, 90, 120])

    # Limits
    min_minutes: int = 1
    max_minutes: int = 180
    jokers_per_week: int = 1
    max_reminder_times: int = 3

    # Schedule times
    morning_prompt_time: str = "07:30"
    daily_check_time: str = "20:00"

    # Media URLs
    horse_happy_images: list[str] = Field(
        default_factory=lambda: [
            "https://images.pexels.com/photos/1996333/pexels-photo-1996333.jpeg",
            "https://images.pexels.com/photos/52500/horse-herd-fog-nature-52500.jpeg",
            "https://images.pexels.com/photos/2749423/pexels-photo-2749423.jpeg",
        ]
    )
    sad_gifs: list[str] = Field(
        default_factory=lambda: [
            "https://media.giphy.com/media/3oz8xKaR836UJOYeOc/giphy.gif",
            "https://media.giphy.com/media/l3vR9O6r8n6u7q1lS/giphy.gif",
            "https://media.giphy.com/media/9Y5BbDSkSTiY8/giphy.gif",
        ]
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("student_chat_id", "parent_chat_id")
    @classmethod
    def validate_chat_id(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError(f"Chat ID must be positive, got {v}")
        return v

    @field_validator("dynamic_planning_times")
    @classmethod
    def validate_times(cls, v: list[str]) -> list[str]:
        for time_str in v:
            try:
                parts = time_str.split(":")
                if len(parts) != 2:
                    raise ValueError(f"Invalid time format: {time_str}")
                hour, minute = int(parts[0]), int(parts[1])
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError(f"Invalid time values: {time_str}")
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid time format: {time_str}: {e}") from e
        return v

    def get_subject_names(self) -> list[str]:
        return [s.name for s in self.allowed_subjects]

    def get_subject_by_name(self, name: str) -> SubjectConfig | None:
        for subject in self.allowed_subjects:
            if subject.name == name:
                return subject
        return None


def load_config() -> BotConfig:
    """
    Load configuration from JSON file with fallback to environment variables.

    Priority:
    1. userconfig/bot_config.json (can be mounted in Docker)
    2. Environment variables
    3. Default values
    """
    config_paths = [
        Path("userconfig/bot_config.json"),
        Path("/app/userconfig/bot_config.json"),
        Path.cwd() / "userconfig" / "bot_config.json",
    ]

    config_data: dict[str, Any] = {}

    for config_path in config_paths:
        if config_path.exists():
            LOGGER.info(f"Loading configuration from {config_path}")
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    config_data = json.load(f)
                LOGGER.info(f"Successfully loaded config from {config_path}")
                break
            except Exception as e:
                LOGGER.warning(f"Failed to load config from {config_path}: {e}")

    # Override with environment variables
    env_overrides = {
        "TELEGRAM_TOKEN": "telegram_token",
        "STUDENT_CHAT_ID": "student_chat_id",
        "PARENT_CHAT_ID": "parent_chat_id",
        "TIMEZONE": "timezone",
        "LOG_LEVEL": "log_level",
        "DATA_DIR": "data_dir",
    }

    for env_key, config_key in env_overrides.items():
        val = os.getenv(env_key)
        if val:
            if config_key in ("student_chat_id", "parent_chat_id"):
                try:
                    config_data[config_key] = int(val)
                except ValueError:
                    LOGGER.warning(f"Invalid {env_key} in environment: {val}")
            else:
                config_data[config_key] = val

    try:
        config = BotConfig(**config_data)
        LOGGER.info("Configuration loaded and validated successfully")
        return config
    except Exception as e:
        LOGGER.error(f"Configuration validation failed: {e}")
        raise
