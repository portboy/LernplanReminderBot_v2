"""Service layer for business logic."""

from __future__ import annotations

import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from models.settings import DayPlan, SettingsRepository, UserSettings, WEEKDAYS

LOGGER = logging.getLogger(__name__)


class LernplanService:
    """Service for managing learning plans."""

    def __init__(self, repo: SettingsRepository, timezone: ZoneInfo):
        self.repo = repo
        self.timezone = timezone

    def get_shared_chat_ids(
        self, student_id: int | None, parent_id: int | None
    ) -> list[int]:
        """Get list of chat IDs that share plans."""
        ids: list[int] = []
        if student_id:
            ids.append(student_id)
        if parent_id and parent_id not in ids:
            ids.append(parent_id)
        return ids

    def get_shared_week_plan(
        self, student_id: int | None, parent_id: int | None
    ) -> dict[str, DayPlan]:
        """Get shared week plan from first available user."""
        for candidate in (student_id, parent_id):
            if candidate is None:
                continue
            settings = self.repo.load(candidate)
            if settings.week_plan:
                return self._clone_week_plan(settings.week_plan)
        return {}

    def sync_week_plan(
        self, new_plan: dict[str, DayPlan], student_id: int | None, parent_id: int | None
    ) -> None:
        """Sync week plan across shared users."""
        plan = self._clone_week_plan(new_plan) if new_plan else {}
        shared_ids = self.get_shared_chat_ids(student_id, parent_id)
        
        if not shared_ids:
            return
        
        for chat_id in shared_ids:
            settings = self.repo.load(chat_id)
            settings.week_plan = self._clone_week_plan(plan)
            self.repo.save(settings)
        
        LOGGER.info(f"Synced week plan to {len(shared_ids)} users")

    def update_day_plan(
        self,
        chat_id: int,
        weekday: str,
        subject: str,
        minutes: int,
        student_id: int | None,
        parent_id: int | None,
    ) -> None:
        """Update plan for a specific day."""
        if chat_id in self.get_shared_chat_ids(student_id, parent_id):
            week_plan = self.get_shared_week_plan(student_id, parent_id)
            week_plan[weekday] = DayPlan(subject=subject, minutes=minutes)
            self.sync_week_plan(week_plan, student_id, parent_id)
        else:
            settings = self.repo.load(chat_id)
            settings.week_plan[weekday] = DayPlan(subject=subject, minutes=minutes)
            self.repo.save(settings)

    def get_today_plan(self, chat_id: int) -> DayPlan | None:
        """Get plan for today."""
        settings = self.repo.load(chat_id)
        now_dt = datetime.now(self.timezone)
        today = WEEKDAYS[now_dt.weekday()]
        return settings.week_plan.get(today)

    def add_dynamic_plan_entry(
        self, chat_id: int, subject: str, time_str: str
    ) -> bool:
        """Add a dynamic plan entry for today."""
        try:
            hh, mm = map(int, time_str.split(":"))
            selected_time = time(hour=hh, minute=mm)
        except (ValueError, AttributeError):
            LOGGER.warning(f"Invalid time format: {time_str}")
            return False

        now_dt = datetime.now(self.timezone)
        target_dt = datetime.combine(now_dt.date(), selected_time, tzinfo=self.timezone)
        
        if target_dt <= now_dt:
            LOGGER.info(f"Time {time_str} is in the past")
            return False

        settings = self.repo.load(chat_id)
        today_iso = now_dt.date().isoformat()
        
        # Clean old entries
        todays_entries = [
            entry for entry in settings.daily_dynamic_plan 
            if entry.get("date_iso") == today_iso
        ]
        if len(todays_entries) != len(settings.daily_dynamic_plan):
            settings.daily_dynamic_plan = todays_entries

        new_entry = {
            "subject": subject,
            "time_str": time_str,
            "completed": False,
            "date_iso": today_iso,
        }
        settings.daily_dynamic_plan.append(new_entry)
        self.repo.save(settings)
        
        LOGGER.info(f"Added dynamic plan for {chat_id}: {subject} at {time_str}")
        return True

    def use_joker(self, chat_id: int) -> bool:
        """Use a joker if available."""
        settings = self.repo.load(chat_id)
        if settings.jokers_available <= 0:
            return False
        
        settings.jokers_available -= 1
        self.repo.save(settings)
        LOGGER.info(f"Joker used by {chat_id}, remaining: {settings.jokers_available}")
        return True

    def get_jokers_available(self, chat_id: int) -> int:
        """Get number of available jokers."""
        settings = self.repo.load(chat_id)
        return max(0, settings.jokers_available)

    def _clone_week_plan(self, plan: dict[str, DayPlan]) -> dict[str, DayPlan]:
        """Clone a week plan."""
        return {
            day: DayPlan(subject=value.subject, minutes=value.minutes)
            for day, value in plan.items()
        }

    def get_weekly_summary(self, chat_id: int) -> dict[str, any]:
        """Get weekly summary statistics."""
        settings = self.repo.load(chat_id)
        planned_days = len(settings.week_plan)
        total_minutes = sum(plan.minutes for plan in settings.week_plan.values())
        
        return {
            "planned_days": planned_days,
            "total_minutes": total_minutes,
            "week_plan": settings.week_plan,
            "reminder_times": settings.reminder_times,
        }
