from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator

LOGGER = logging.getLogger(__name__)

WEEKDAYS = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"]


class DayPlanModel(BaseModel):
    """Pydantic model for day planning with validation."""

    subject: str = Field(..., min_length=1, max_length=50)
    minutes: int = Field(..., ge=1, le=300)

    @field_validator("minutes")
    @classmethod
    def validate_minutes(cls, v: int) -> int:
        """Ensure minutes are positive."""
        if v < 0:
            raise ValueError("Minutes must be positive")
        return v


@dataclass
class DayPlan:
    """Legacy dataclass for backward compatibility."""

    subject: str
    minutes: int

    def to_dict(self) -> dict:
        return {"subject": self.subject, "minutes": self.minutes}

    @staticmethod
    def from_dict(data: dict) -> "DayPlan":
        # Validate using Pydantic
        validated = DayPlanModel(subject=data["subject"], minutes=int(data["minutes"]))
        return DayPlan(subject=validated.subject, minutes=validated.minutes)


@dataclass
class UserSettings:
    chat_id: int
    reminder_times: List[str] = field(default_factory=list)  # HH:MM (24h)
    week_plan: Dict[str, DayPlan] = field(default_factory=dict)  # weekday(lower)->DayPlan
    jokers_available: int = 1
    last_joker_reset_iso: str = ""
    daily_dynamic_plan: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "reminder_times": self.reminder_times,
            "week_plan": {k: v.to_dict() for k, v in self.week_plan.items()},
            "jokers_available": self.jokers_available,
            "last_joker_reset_iso": self.last_joker_reset_iso,
            "daily_dynamic_plan": [dict(entry) for entry in self.daily_dynamic_plan],
        }

    @staticmethod
    def from_dict(data: dict) -> "UserSettings":
        week_plan = {k: DayPlan.from_dict(v) for k, v in data.get("week_plan", {}).items()}
        raw_daily_plan = data.get("daily_dynamic_plan", [])
        if not isinstance(raw_daily_plan, list):
            raw_daily_plan = []
        daily_dynamic_plan: List[Dict[str, Any]] = [
            dict(item) for item in raw_daily_plan if isinstance(item, dict)
        ]
        last_reset = data.get("last_joker_reset_iso")
        last_reset_str = last_reset if isinstance(last_reset, str) else ""
        return UserSettings(
            chat_id=int(data["chat_id"]),
            reminder_times=list(data.get("reminder_times", [])),
            week_plan=week_plan,
            jokers_available=int(data.get("jokers_available", 1)),
            last_joker_reset_iso=last_reset_str,
            daily_dynamic_plan=daily_dynamic_plan,
        )

    def ensure_recent_joker_reset(self, reference_date: date | None = None) -> bool:
        reference_date = reference_date or date.today()
        last_monday = reference_date - timedelta(days=reference_date.weekday())
        last_monday_iso = last_monday.isoformat()
        last_reset_date: date | None = None
        if self.last_joker_reset_iso:
            try:
                last_reset_date = date.fromisoformat(self.last_joker_reset_iso)
            except ValueError:
                last_reset_date = None
        if last_reset_date is None or last_reset_date < last_monday:
            self.jokers_available = 1
            self.last_joker_reset_iso = last_monday_iso
            return True
        return False


class SettingsRepository:
    """Repository for user settings with anonymized filenames."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._id_cache: dict[int, str] = {}  # chat_id -> filename mapping

    def _hash_chat_id(self, chat_id: int) -> str:
        """Generate anonymized filename from chat_id."""
        if chat_id in self._id_cache:
            return self._id_cache[chat_id]
        
        # Use SHA256 hash for anonymization
        hash_obj = hashlib.sha256(str(chat_id).encode())
        hashed = hash_obj.hexdigest()[:16]  # Use first 16 chars
        self._id_cache[chat_id] = hashed
        return hashed

    def _file_for(self, chat_id: int) -> Path:
        """Get file path for chat_id with anonymization."""
        hashed = self._hash_chat_id(chat_id)
        return self.base_path / f"user_{hashed}.json"

    def _load_mapping(self) -> dict[str, int]:
        """Load chat_id mapping file."""
        mapping_file = self.base_path / "id_mapping.json"
        if mapping_file.exists():
            try:
                with mapping_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {k: int(v) for k, v in data.items()}
            except Exception as e:
                LOGGER.warning(f"Failed to load ID mapping: {e}")
        return {}

    def _save_mapping(self) -> None:
        """Save chat_id mapping for recovery."""
        mapping_file = self.base_path / "id_mapping.json"
        try:
            # Load existing mapping
            existing = self._load_mapping()
            # Add current cache entries
            for chat_id, hashed in self._id_cache.items():
                existing[hashed] = chat_id
            
            with mapping_file.open("w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            LOGGER.error(f"Failed to save ID mapping: {e}")

    def load(self, chat_id: int) -> UserSettings:
        f = self._file_for(chat_id)
        if not f.exists():
            # Migrate old format (user_<chat_id>.json)
            old_file = self.base_path / f"user_{chat_id}.json"
            if old_file.exists():
                LOGGER.info(f"Migrating old format file for chat {chat_id}")
                try:
                    old_file.rename(f)
                except Exception as e:
                    LOGGER.warning(f"Failed to migrate file: {e}")
            else:
                settings = UserSettings(chat_id=chat_id)
                settings.ensure_recent_joker_reset()
                return settings
        
        try:
            with f.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            settings = UserSettings.from_dict(data)
            if settings.ensure_recent_joker_reset():
                self.save(settings)
            return settings
        except Exception as e:
            LOGGER.error(f"Failed to load settings for chat {chat_id}: {e}")
            settings = UserSettings(chat_id=chat_id)
            settings.ensure_recent_joker_reset()
            return settings

    def save(self, settings: UserSettings) -> None:
        f = self._file_for(settings.chat_id)
        try:
            with f.open("w", encoding="utf-8") as fh:
                json.dump(settings.to_dict(), fh, ensure_ascii=False, indent=2)
            # Update mapping
            self._save_mapping()
        except Exception as e:
            LOGGER.error(f"Failed to save settings for chat {settings.chat_id}: {e}")
            raise

    def list_user_ids(self) -> list[int]:
        ids: list[int] = []
        
        # Try to use mapping file
        mapping = self._load_mapping()
        if mapping:
            return list(mapping.values())
        
        # Fallback: scan for old format files
        for file in self.base_path.glob("user_*.json"):
            if file.name == "id_mapping.json":
                continue
            try:
                # Try old format first
                parts = file.stem.split("_", 1)
                if len(parts) == 2:
                    try:
                        num = int(parts[1])
                        ids.append(num)
                    except ValueError:
                        pass
            except Exception:
                continue
        return ids

