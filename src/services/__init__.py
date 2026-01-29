"""Service layer for business logic."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
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

    def get_weekly_statistics(self, chat_id: int, days: int = 7) -> dict[str, any]:
        """Calculate weekly statistics from completed dynamic plan entries.
        
        Args:
            chat_id: User's chat ID
            days: Number of days to look back (default 7)
            
        Returns:
            Dictionary with total_minutes and subject_minutes
        """
        settings = self.repo.load(chat_id)
        
        # Calculate date range
        today = datetime.now(self.timezone).date()
        start_date = today - timedelta(days=days - 1)
        
        # Aggregate completed entries by subject
        subject_minutes: dict[str, int] = {}
        total_minutes = 0
        
        for entry in settings.daily_dynamic_plan:
            # Only count completed entries
            if not entry.get("completed"):
                continue
                
            # Check if entry is within date range
            entry_date_str = entry.get("date_iso")
            if not entry_date_str:
                continue
                
            try:
                entry_date = datetime.fromisoformat(entry_date_str).date()
            except (ValueError, TypeError):
                continue
                
            if entry_date < start_date or entry_date > today:
                continue
            
            # Get subject and add to plan (we don't have duration in dynamic plan)
            # Check if there's a week plan for this day to get duration
            weekday = WEEKDAYS[entry_date.weekday()]
            subject = entry.get("subject", "Unbekannt")
            
            # Try to get duration from week_plan
            day_plan = settings.week_plan.get(weekday)
            if day_plan and day_plan.subject == subject:
                minutes = day_plan.minutes
            else:
                # Default estimate: 30 minutes per completed entry
                minutes = 30
            
            subject_minutes[subject] = subject_minutes.get(subject, 0) + minutes
            total_minutes += minutes
        
        return {
            "total_minutes": total_minutes,
            "subject_minutes": subject_minutes,
            "start_date": start_date.strftime("%d.%m.%Y"),
            "end_date": today.strftime("%d.%m.%Y"),
            "days": days,
        }
