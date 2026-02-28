from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

LOGGER = logging.getLogger(__name__)

WEEKDAYS = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"]
ALLOWED_SUBJECTS = ["Mathe", "Englisch"]  # aktuell begrenzt laut Spezifikation


@dataclass
class DayPlan:
    subject: str
    minutes: int

    def to_dict(self) -> dict:
        return {"subject": self.subject, "minutes": self.minutes}

    @staticmethod
    def from_dict(data: dict) -> "DayPlan":
        return DayPlan(subject=data["subject"], minutes=int(data["minutes"]))


@dataclass
class UserSettings:
    chat_id: int
    reminder_times: List[str] = field(default_factory=list)  # HH:MM (24h)
    week_plan: Dict[str, DayPlan] = field(default_factory=dict)  # weekday(lower)->DayPlan
    jokers_available: int = 1
    last_joker_reset_iso: str = ""
    daily_dynamic_plan: List[Dict[str, Any]] = field(default_factory=list)
    learning_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "reminder_times": self.reminder_times,
            "week_plan": {k: v.to_dict() for k, v in self.week_plan.items()},
            "jokers_available": self.jokers_available,
            "last_joker_reset_iso": self.last_joker_reset_iso,
            "daily_dynamic_plan": [dict(entry) for entry in self.daily_dynamic_plan],
            "learning_history": [dict(entry) for entry in self.learning_history],
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
        raw_history = data.get("learning_history", [])
        if not isinstance(raw_history, list):
            raw_history = []
        learning_history: List[Dict[str, Any]] = [
            dict(item) for item in raw_history if isinstance(item, dict)
        ]
        return UserSettings(
            chat_id=int(data["chat_id"]),
            reminder_times=list(data.get("reminder_times", [])),
            week_plan=week_plan,
            jokers_available=int(data.get("jokers_available", 1)),
            last_joker_reset_iso=last_reset_str,
            daily_dynamic_plan=daily_dynamic_plan,
            learning_history=learning_history,
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
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _file_for(self, chat_id: int) -> Path:
        return self.base_path / f"user_{chat_id}.json"

    def load(self, chat_id: int) -> UserSettings:
        f = self._file_for(chat_id)
        if not f.exists():
            # default week plan empty; subject fallback handled elsewhere
            settings = UserSettings(chat_id=chat_id)
            settings.ensure_recent_joker_reset()
            return settings
        with f.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        settings = UserSettings.from_dict(data)
        if settings.ensure_recent_joker_reset():
            self.save(settings)
        return settings

    def save(self, settings: UserSettings) -> None:
        """Save settings atomically via write-to-temp + rename."""
        f = self._file_for(settings.chat_id)
        data = settings.to_dict()
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.base_path), suffix=".tmp", prefix="user_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(f))  # atomic on same filesystem
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def list_user_ids(self) -> list[int]:
        ids: list[int] = []
        for file in self.base_path.glob("user_*.json"):
            try:
                num = int(file.stem.split("_", 1)[1])
                ids.append(num)
            except Exception:
                continue
        return ids
