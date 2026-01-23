from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

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

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "reminder_times": self.reminder_times,
            "week_plan": {k: v.to_dict() for k, v in self.week_plan.items()},
        }

    @staticmethod
    def from_dict(data: dict) -> "UserSettings":
        week_plan = {k: DayPlan.from_dict(v) for k, v in data.get("week_plan", {}).items()}
        return UserSettings(
            chat_id=int(data["chat_id"]),
            reminder_times=list(data.get("reminder_times", [])),
            week_plan=week_plan,
        )


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
            return UserSettings(chat_id=chat_id)
        with f.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return UserSettings.from_dict(data)

    def save(self, settings: UserSettings) -> None:
        f = self._file_for(settings.chat_id)
        with f.open("w", encoding="utf-8") as fh:
            json.dump(settings.to_dict(), fh, ensure_ascii=False, indent=2)

    def list_user_ids(self) -> list[int]:
        ids: list[int] = []
        for file in self.base_path.glob("user_*.json"):
            try:
                num = int(file.stem.split("_", 1)[1])
                ids.append(num)
            except Exception:
                continue
        return ids
