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

    # ------------------------------------------------------------------
    # Shared state helpers
    # ------------------------------------------------------------------

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
        plan = self._clone_week_plan(new_plan) if new_plan else {}
        shared_ids = self.get_shared_chat_ids(student_id, parent_id)
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
        if chat_id in self.get_shared_chat_ids(student_id, parent_id):
            week_plan = self.get_shared_week_plan(student_id, parent_id)
            week_plan[weekday] = DayPlan(subject=subject, minutes=minutes)
            self.sync_week_plan(week_plan, student_id, parent_id)
        else:
            settings = self.repo.load(chat_id)
            settings.week_plan[weekday] = DayPlan(subject=subject, minutes=minutes)
            self.repo.save(settings)

    # ------------------------------------------------------------------
    # Reminder time management
    # ------------------------------------------------------------------

    def get_shared_reminder_times(
        self, student_id: int | None, parent_id: int | None
    ) -> list[str]:
        """Return the shared reminder times (prioritizes student)."""
        for candidate in (student_id, parent_id):
            if candidate is None:
                continue
            settings = self.repo.load(candidate)
            if settings.reminder_times:
                return list(settings.reminder_times)
        return []

    def sync_reminder_times(
        self,
        new_times: list[str],
        student_id: int | None,
        parent_id: int | None,
    ) -> None:
        """Synchronize reminder times across shared users."""
        shared_ids = self.get_shared_chat_ids(student_id, parent_id)
        for chat_id in shared_ids:
            settings = self.repo.load(chat_id)
            settings.reminder_times = list(new_times)
            self.repo.save(settings)
        LOGGER.info(f"Synced reminder times {new_times} to {len(shared_ids)} users")

    def add_reminder_time(
        self,
        chat_id: int,
        time_str: str,
        max_times: int,
        student_id: int | None,
        parent_id: int | None,
    ) -> tuple[bool, str]:
        """Add a reminder time. Returns (success, message)."""
        # Validate format
        try:
            parts = time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
            normalized = f"{hour:02d}:{minute:02d}"
        except (ValueError, IndexError, AttributeError):
            return False, f"Ungültiges Zeitformat: {time_str}. Bitte HH:MM verwenden."

        # Get current times
        if chat_id in self.get_shared_chat_ids(student_id, parent_id):
            current = self.get_shared_reminder_times(student_id, parent_id)
        else:
            current = list(self.repo.load(chat_id).reminder_times)

        if normalized in current:
            return False, f"⏰ {normalized} ist bereits vorhanden."

        if len(current) >= max_times:
            return False, f"Maximal {max_times} Erinnerungszeiten erlaubt."

        current.append(normalized)
        current.sort()

        # Sync
        if chat_id in self.get_shared_chat_ids(student_id, parent_id):
            self.sync_reminder_times(current, student_id, parent_id)
        else:
            settings = self.repo.load(chat_id)
            settings.reminder_times = current
            self.repo.save(settings)

        return True, f"✅ Erinnerung um {normalized} hinzugefügt."

    def remove_reminder_time(
        self,
        chat_id: int,
        time_str: str,
        student_id: int | None,
        parent_id: int | None,
    ) -> tuple[bool, str]:
        """Remove a reminder time. Returns (success, message)."""
        if chat_id in self.get_shared_chat_ids(student_id, parent_id):
            current = self.get_shared_reminder_times(student_id, parent_id)
        else:
            current = list(self.repo.load(chat_id).reminder_times)

        if time_str not in current:
            return False, f"⏰ {time_str} ist nicht vorhanden."

        current.remove(time_str)

        if chat_id in self.get_shared_chat_ids(student_id, parent_id):
            self.sync_reminder_times(current, student_id, parent_id)
        else:
            settings = self.repo.load(chat_id)
            settings.reminder_times = current
            self.repo.save(settings)

        return True, f"🗑️ Erinnerung um {time_str} entfernt."

    # ------------------------------------------------------------------
    # Today / dynamic planning
    # ------------------------------------------------------------------

    def get_today_plan(self, chat_id: int) -> DayPlan | None:
        settings = self.repo.load(chat_id)
        now_dt = datetime.now(self.timezone)
        today = WEEKDAYS[now_dt.weekday()]
        return settings.week_plan.get(today)

    def add_dynamic_plan_entry(
        self, chat_id: int, subject: str, time_str: str
    ) -> bool:
        try:
            hh, mm = map(int, time_str.split(":"))
            selected_time = time(hour=hh, minute=mm)
        except (ValueError, AttributeError):
            return False

        now_dt = datetime.now(self.timezone)
        target_dt = datetime.combine(now_dt.date(), selected_time, tzinfo=self.timezone)

        if target_dt <= now_dt:
            return False

        settings = self.repo.load(chat_id)
        today_iso = now_dt.date().isoformat()

        # Clean old entries
        settings.daily_dynamic_plan = [
            e for e in settings.daily_dynamic_plan if e.get("date_iso") == today_iso
        ]

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

    # ------------------------------------------------------------------
    # Joker
    # ------------------------------------------------------------------

    def use_joker(self, chat_id: int) -> bool:
        settings = self.repo.load(chat_id)
        if settings.jokers_available <= 0:
            return False
        settings.jokers_available -= 1
        self.repo.save(settings)
        LOGGER.info(f"Joker used by {chat_id}, remaining: {settings.jokers_available}")
        return True

    def get_jokers_available(self, chat_id: int) -> int:
        settings = self.repo.load(chat_id)
        return max(0, settings.jokers_available)

    # ------------------------------------------------------------------
    # Learning history & statistics
    # ------------------------------------------------------------------

    def archive_daily_to_history(
        self, chat_id: int, learned_response: str | None = None
    ) -> int:
        """Archive today's completed dynamic entries into learning_history.

        Call this at the end of the day *before* clearing daily_dynamic_plan.
        Returns number of archived entries.
        """
        settings = self.repo.load(chat_id)
        now_dt = datetime.now(self.timezone)
        today = WEEKDAYS[now_dt.weekday()]
        today_iso = now_dt.date().isoformat()

        archived = 0
        for entry in settings.daily_dynamic_plan:
            if entry.get("date_iso") != today_iso:
                continue
            history_entry = {
                "date_iso": today_iso,
                "weekday": today,
                "subject": entry.get("subject", "Unbekannt"),
                "time_str": entry.get("time_str", ""),
                "completed": bool(entry.get("completed")),
                "timestamp": now_dt.isoformat(),
            }
            if learned_response:
                history_entry["learned_response"] = learned_response
            settings.learning_history.append(history_entry)
            archived += 1

        # Also archive the weekly plan entry for today if exists
        day_plan = settings.week_plan.get(today)
        if day_plan and not any(
            e.get("date_iso") == today_iso and e.get("source") == "week_plan"
            for e in settings.learning_history
        ):
            settings.learning_history.append({
                "date_iso": today_iso,
                "weekday": today,
                "subject": day_plan.subject,
                "planned_minutes": day_plan.minutes,
                "source": "week_plan",
                "learned_response": learned_response or "",
                "timestamp": now_dt.isoformat(),
            })
            archived += 1

        if archived > 0:
            self.repo.save(settings)
            LOGGER.info(f"Archived {archived} entries to history for chat {chat_id}")

        return archived

    def get_weekly_summary(self, chat_id: int) -> dict[str, any]:
        settings = self.repo.load(chat_id)
        return {
            "planned_days": len(settings.week_plan),
            "total_minutes": sum(p.minutes for p in settings.week_plan.values()),
            "week_plan": settings.week_plan,
            "reminder_times": settings.reminder_times,
        }

    def get_weekly_statistics(self, chat_id: int, days: int = 7) -> dict[str, any]:
        """Calculate weekly statistics from learning_history (persisted data).

        Returns dict with total_minutes, subject_minutes, days_learned, etc.
        """
        settings = self.repo.load(chat_id)

        today = datetime.now(self.timezone).date()
        start_date = today - timedelta(days=days - 1)

        subject_minutes: dict[str, int] = {}
        total_minutes = 0
        days_with_learning: set[str] = set()

        for entry in settings.learning_history:
            entry_date_str = entry.get("date_iso")
            if not entry_date_str:
                continue
            try:
                entry_date = datetime.fromisoformat(entry_date_str).date()
            except (ValueError, TypeError):
                continue
            if entry_date < start_date or entry_date > today:
                continue

            subject = entry.get("subject", "Unbekannt")

            # Use planned_minutes if available, otherwise try to infer
            minutes = entry.get("planned_minutes", 0)
            if not minutes:
                weekday = entry.get("weekday", "")
                day_plan = settings.week_plan.get(weekday)
                if day_plan and day_plan.subject == subject:
                    minutes = day_plan.minutes
                else:
                    minutes = 30  # default estimate

            # Only count entries where learning happened
            response = entry.get("learned_response", "")
            was_completed = entry.get("completed", False)
            if response == "no" and not was_completed:
                continue

            subject_minutes[subject] = subject_minutes.get(subject, 0) + minutes
            total_minutes += minutes
            days_with_learning.add(entry_date_str)

        return {
            "total_minutes": total_minutes,
            "subject_minutes": subject_minutes,
            "days_learned": len(days_with_learning),
            "start_date": start_date.strftime("%d.%m.%Y"),
            "end_date": today.strftime("%d.%m.%Y"),
            "days": days,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clone_week_plan(self, plan: dict[str, DayPlan]) -> dict[str, DayPlan]:
        return {
            day: DayPlan(subject=v.subject, minutes=v.minutes)
            for day, v in plan.items()
        }
