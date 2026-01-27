"""Message builders and formatters."""

from __future__ import annotations

from datetime import datetime
from random import choice
from zoneinfo import ZoneInfo

from core.config import BotConfig
from models.settings import DayPlan, UserSettings, WEEKDAYS


class MessageBuilder:
    """Builder for message texts."""

    def __init__(self, config: BotConfig, timezone: ZoneInfo):
        self.config = config
        self.timezone = timezone

    def format_duration(self, minutes: int) -> str:
        """Format duration in hours and minutes."""
        if minutes <= 0:
            return "0min"
        hours, remainder = divmod(minutes, 60)
        fragments: list[str] = []
        if hours:
            fragments.append(f"{hours}h")
        if remainder:
            fragments.append(f"{remainder}min")
        return " ".join(fragments) if fragments else "0min"

    def format_total_minutes(self, minutes: int) -> str:
        """Format total minutes."""
        if minutes <= 0:
            return "0 Minuten"
        return self.format_duration(minutes)

    def reminder_time_icon(self, time_str: str) -> str:
        """Get icon based on time of day."""
        try:
            hour = int(time_str.split(":")[0])
        except (ValueError, IndexError):
            return "⏰"
        if 5 <= hour < 9:
            return "🌅"
        if 9 <= hour < 16:
            return "☀️"
        if 16 <= hour < 19:
            return "🌆"
        if 19 <= hour < 22:
            return "🌙"
        if 22 <= hour < 24:
            return "🌙"
        return "🌙"

    def build_reminder_message(self, settings: UserSettings) -> str:
        """Build a reminder message for the current day."""
        now_dt = datetime.now(self.timezone)
        today = WEEKDAYS[now_dt.weekday()]
        today_iso = now_dt.date().isoformat()
        lines = [f"📌 Erinnerung für {today.capitalize()}"]

        day_plan = settings.week_plan.get(today)
        if day_plan:
            duration = self.format_duration(day_plan.minutes)
            # Try to get emoji from config
            subject_config = self.config.get_subject_by_name(day_plan.subject)
            emoji = subject_config.emoji if subject_config else "📘"
            lines.append(f"{emoji} {day_plan.subject} ({duration})")
        else:
            lines.append("📘 Keine feste Aufgabe hinterlegt.")

        dynamic_entries = [
            entry
            for entry in settings.daily_dynamic_plan
            if entry.get("date_iso") == today_iso
        ]
        if dynamic_entries:
            lines.append("🔁 Dynamische Einträge:")
            for entry in dynamic_entries:
                status = "✅" if entry.get("completed") else "⬜"
                entry_time = entry.get("time_str", "--:--")
                subject = entry.get("subject", "Unbekannt")
                lines.append(f"{status} {entry_time} – {subject}")
        else:
            lines.append("🔁 Keine dynamischen Einträge für heute.")

        return "\n".join(lines)

    def build_weekly_overview(
        self, week_plan: dict[str, DayPlan], reminder_times: list[str]
    ) -> str:
        """Build a professional weekly overview with formatted table."""
        day_icons = {
            "montag": "🔵",
            "dienstag": "🟢",
            "mittwoch": "🟡",
            "donnerstag": "🟠",
            "freitag": "🟣",
            "samstag": "🟤",
            "sonntag": "⚪",
        }

        overview_lines: list[str] = [
            "📊 **WOCHENÜBERSICHT**",
            "```",
            "┌─────────────┬─────────────┬────────┐",
            "│ Tag         │ Fach        │ Zeit   │",
            "├─────────────┼─────────────┼────────┤",
        ]

        for weekday in WEEKDAYS:
            plan = week_plan.get(weekday)
            day_label = weekday.capitalize()
            if plan:
                subject = plan.subject
                duration = self.format_duration(plan.minutes)
            else:
                subject = "---"
                duration = "---"
            overview_lines.append(f"│ {day_label:<11} │ {subject:<11} │ {duration:<6} │")

        overview_lines.extend(
            [
                "└─────────────┴─────────────┴────────┘",
                "```",
                "",
                "📈 **ZUSAMMENFASSUNG**",
            ]
        )

        planned_days = len(week_plan)
        total_minutes = sum(plan.minutes for plan in week_plan.values())
        overview_lines.append(f"📅 Geplante Tage: {planned_days}/7")
        overview_lines.append(f"⏱️ Gesamtzeit: {self.format_total_minutes(total_minutes)}")
        overview_lines.append("")
        overview_lines.append("📌 Tagesfarben:")
        overview_lines.append(
            " ".join(f"{day_icons.get(day, '•')} {day[:2].upper()}" for day in WEEKDAYS)
        )
        overview_lines.append("")
        overview_lines.append("⏰ **ERINNERUNGSZEITEN**")

        if reminder_times:
            for reminder in sorted(reminder_times):
                overview_lines.append(
                    f"{self.reminder_time_icon(reminder)} **{reminder}**"
                )
        else:
            overview_lines.append("Keine Erinnerungszeiten")

        return "\n".join(overview_lines)

    def build_daily_report(
        self, dynamic_entries: list[dict], completed_count: int, date_str: str
    ) -> str:
        """Build daily report for dynamic planning."""
        report_lines = [
            "📋 Tagesreport – Dynamische Planung",
            f"Datum: {date_str}",
        ]
        
        if dynamic_entries:
            for entry in dynamic_entries:
                status = "✅" if entry.get("completed") else "⬜"
                subject = entry.get("subject", "Unbekannt")
                time_str = entry.get("time_str", "--:--")
                report_lines.append(f"{status} {time_str} – {subject}")
        else:
            report_lines.append("Keine spontanen Lernpläne für heute hinterlegt.")
        
        report_lines.append(f"Erledigt: {completed_count}/{len(dynamic_entries)}")
        return "\n".join(report_lines)

    def get_funny_error(self) -> str:
        """Get a random funny error message."""
        messages = [
            "🤔 Das hat nicht geklappt! Selbst ein Einhorn wäre verwirrt...",
            "🦄 Ups! Das war wohl nichts. Versuch's nochmal, du schaffst das!",
            "😅 Oh nein! Das ging schief wie ein Pingpong-Ball im Tornado!",
            "🎭 Autsch! Das war ein kreativer Versuch, aber leider daneben...",
            "🚀 Houston, wir haben ein Problem! (Aber es ist lösbar!)",
            "🎪 Das war eine interessante Eingabe, aber der Bot ist verwirrt!",
            "🎨 Kreativ, aber leider nicht das, was ich erwartet habe!",
            "🎪 Abrakadabra... och, der Zauber hat nicht funktioniert!",
        ]
        return choice(messages)

    def get_funny_number_error(self) -> str:
        """Get a random funny number error message."""
        messages = [
            f"🔢 Diese Zahl ist mir zu mystisch! Ich brauche was zwischen {self.config.min_minutes} und {self.config.max_minutes}.",
            f"🎯 Knapp daneben! Zahlen zwischen {self.config.min_minutes} und {self.config.max_minutes} sind perfekt!",
            f"🎪 Diese Zahl ist außerhalb meines Universums! {self.config.min_minutes}-{self.config.max_minutes} bitte!",
            f"🚀 Diese Zahl ist zu weit weg! Bleib zwischen {self.config.min_minutes} und {self.config.max_minutes}.",
        ]
        return choice(messages)

    def get_random_happy_image(self) -> str:
        """Get random happy horse image."""
        return choice(self.config.horse_happy_images)

    def get_random_sad_gif(self) -> str:
        """Get random sad GIF."""
        return choice(self.config.sad_gifs)
