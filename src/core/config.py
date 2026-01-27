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
    data_dir: str = "data"
    config_dir: str = "userconfig"
    
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
    duration_choices: list[int] = Field(
        default_factory=lambda: [15, 30, 45, 60, 90, 120]
    )
    
    # Limits
    min_minutes: int = 1
    max_minutes: int = 180
    jokers_per_week: int = 1
    
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
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("student_chat_id", "parent_chat_id")
    @classmethod
    def validate_chat_id(cls, v: int | None) -> int | None:
        """Validate chat IDs are positive integers."""
        if v is not None and v <= 0:
            raise ValueError(f"Chat ID must be positive, got {v}")
        return v

    @field_validator("dynamic_planning_times")
    @classmethod
    def validate_times(cls, v: list[str]) -> list[str]:
        """Validate time format HH:MM."""
        for time_str in v:
            try:
                parts = time_str.split(":")
                if len(parts) != 2:
                    raise ValueError(f"Invalid time format: {time_str}")
                hour, minute = int(parts[0]), int(parts[1])
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError(f"Invalid time values: {time_str}")
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid time format: {time_str}: {e}")
        return v

    def get_subject_names(self) -> list[str]:
        """Get list of subject names."""
        return [s.name for s in self.allowed_subjects]

    def get_subject_by_name(self, name: str) -> SubjectConfig | None:
        """Get subject config by name."""
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
    # Try to find config file
    config_paths = [
        Path("userconfig/bot_config.json"),
        Path("/app/userconfig/bot_config.json"),  # Docker path
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
    if os.getenv("TELEGRAM_TOKEN"):
        config_data["telegram_token"] = os.getenv("TELEGRAM_TOKEN")
    
    if os.getenv("STUDENT_CHAT_ID"):
        try:
            config_data["student_chat_id"] = int(os.getenv("STUDENT_CHAT_ID"))
        except ValueError:
            LOGGER.warning("Invalid STUDENT_CHAT_ID in environment")
    
    if os.getenv("PARENT_CHAT_ID"):
        try:
            config_data["parent_chat_id"] = int(os.getenv("PARENT_CHAT_ID"))
        except ValueError:
            LOGGER.warning("Invalid PARENT_CHAT_ID in environment")
    
    if os.getenv("TIMEZONE"):
        config_data["timezone"] = os.getenv("TIMEZONE")
    
    if os.getenv("LOG_LEVEL"):
        config_data["log_level"] = os.getenv("LOG_LEVEL")
    
    if os.getenv("DATA_DIR"):
        config_data["data_dir"] = os.getenv("DATA_DIR")
    
    # Create and validate config
    try:
        config = BotConfig(**config_data)
        LOGGER.info("Configuration loaded and validated successfully")
        return config
    except Exception as e:
        LOGGER.error(f"Configuration validation failed: {e}")
        raise


def save_config_template(path: Path) -> None:
    """Save a template configuration file."""
    template = BotConfig(
        telegram_token="YOUR_BOT_TOKEN_HERE",
        student_chat_id=None,
        parent_chat_id=None,
    )
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(template.model_dump(), f, indent=2, ensure_ascii=False)
    
    LOGGER.info(f"Configuration template saved to {path}")
