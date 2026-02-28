"""Message builders and formatters."""

from __future__ import annotations

from datetime import datetime
from random import choice
from zoneinfo import ZoneInfo

from core.config import BotConfig
from models.settings import WEEKDAYS, DayPlan, UserSettings


class MessageBuilder:
    """Builder for message texts."""

    def __init__(self, config: BotConfig, timezone: ZoneInfo):
        self.config = config
        self.timezone = timezone

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def format_duration(self, minutes: int) -> str:
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
        if minutes <= 0:
            return "0 Minuten"
        return self.format_duration(minutes)

    def reminder_time_icon(self, time_str: str) -> str:
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
        return "🌙"

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def build_reminder_message(self, settings: UserSettings) -> str:
        now_dt = datetime.now(self.timezone)
        today = WEEKDAYS[now_dt.weekday()]
        today_iso = now_dt.date().isoformat()
        lines = [f"📌 Erinnerung für {today.capitalize()}"]

        day_plan = settings.week_plan.get(today)
        if day_plan:
            sc = self.config.get_subject_by_name(day_plan.subject)
            emoji = sc.emoji if sc else "📘"
            lines.append(f"{emoji} {day_plan.subject} ({self.format_duration(day_plan.minutes)})")
        else:
            lines.append("📘 Keine feste Aufgabe hinterlegt.")

        dynamic = [e for e in settings.daily_dynamic_plan if e.get("date_iso") == today_iso]
        if dynamic:
            lines.append("🔁 Dynamische Einträge:")
            for entry in dynamic:
                status = "✅" if entry.get("completed") else "⬜"
                subj = entry.get("subject", "Unbekannt")
                t = entry.get("time_str", "--:--")
                lines.append(f"{status} {t} – {subj}")
        else:
            lines.append("🔁 Keine dynamischen Einträge für heute.")

        return "\n".join(lines)

    def build_today_overview(self, settings: UserSettings) -> str:
        now_dt = datetime.now(self.timezone)
        today = WEEKDAYS[now_dt.weekday()]
        today_iso = now_dt.date().isoformat()
        current_time = now_dt.strftime("%H:%M")

        lines = [
            f"📌 **HEUTE: {today.upper()}**",
            f"🕐 Aktuelle Zeit: {current_time}",
            "",
        ]

        day_plan = settings.week_plan.get(today)
        if day_plan:
            sc = self.config.get_subject_by_name(day_plan.subject)
            emoji = sc.emoji if sc else "📘"
            lines.append("📚 **Wochenplan:**")
            lines.append(f"{emoji} {day_plan.subject} — {self.format_duration(day_plan.minutes)}")
        else:
            lines.append("📚 **Wochenplan:** Nichts geplant")

        lines.append("")

        dynamic = [e for e in settings.daily_dynamic_plan if e.get("date_iso") == today_iso]
        if dynamic:
            lines.append("🔔 **Erinnerungen heute:**")
            for entry in sorted(dynamic, key=lambda e: e.get("time_str", "")):
                sc = self.config.get_subject_by_name(entry.get("subject", ""))
                emoji = sc.emoji if sc else "📘"
                status = "✅" if entry.get("completed") else "⏰"
                subj = entry.get("subject", "Unbekannt")
                t = entry.get("time_str", "--:--")
                lines.append(f"{status} {t} — {emoji} {subj}")
        else:
            lines.append("🔔 **Erinnerungen heute:** Keine")

        lines.append("")
        lines.append(f"🃏 Joker übrig: {settings.jokers_available}/{self.config.jokers_per_week}")
        return "\n".join(lines)

    def build_weekly_overview(
        self, week_plan: dict[str, DayPlan], reminder_times: list[str]
    ) -> str:
        now_dt = datetime.now(self.timezone)
        today = WEEKDAYS[now_dt.weekday()]

        day_icons = {
            "montag": "🔵",
            "dienstag": "🟢",
            "mittwoch": "🟡",
            "donnerstag": "🟠",
            "freitag": "🟣",
            "samstag": "🟤",
            "sonntag": "⚪",
        }

        lines: list[str] = ["📊 **WOCHENÜBERSICHT**", ""]

        for weekday in WEEKDAYS:
            plan = week_plan.get(weekday)
            icon = day_icons.get(weekday, "⚪")
            label = weekday.capitalize()
            indicator = "➤ " if weekday == today else ""

            if plan:
                sc = self.config.get_subject_by_name(plan.subject)
                emoji = sc.emoji if sc else "📘"
                dur = self.format_duration(plan.minutes)
                lines.append(f"{indicator}{icon} **{label}**\n   {emoji} {plan.subject} • {dur}")
            else:
                lines.append(f"{indicator}{icon} **{label}**\n   — Nichts geplant")
            lines.append("")

        planned_days = len(week_plan)
        total_minutes = sum(p.minutes for p in week_plan.values())

        lines.extend(
            [
                "━━━━━━━━━━━━━━━━━━━━",
                "📈 **ZUSAMMENFASSUNG**",
                "",
                f"📅 Geplante Tage: **{planned_days}/7**",
                f"⏱️ Gesamtzeit: **{self.format_total_minutes(total_minutes)}**",
            ]
        )

        if reminder_times:
            lines.extend(["", "⏰ **ERINNERUNGSZEITEN**"])
            for r in sorted(reminder_times):
                lines.append(f"{self.reminder_time_icon(r)} {r}")
        else:
            lines.extend(["", "⏰ Keine Erinnerungszeiten gesetzt"])

        return "\n".join(lines)

    def build_daily_report(
        self, dynamic_entries: list[dict], completed_count: int, date_str: str
    ) -> str:
        lines = ["📋 Tagesreport – Dynamische Planung", f"Datum: {date_str}"]
        if dynamic_entries:
            for entry in dynamic_entries:
                status = "✅" if entry.get("completed") else "⬜"
                subj = entry.get("subject", "Unbekannt")
                t = entry.get("time_str", "--:--")
                lines.append(f"{status} {t} – {subj}")
        else:
            lines.append("Keine spontanen Lernpläne für heute hinterlegt.")
        lines.append(f"Erledigt: {completed_count}/{len(dynamic_entries)}")
        return "\n".join(lines)

    def build_weekly_statistics(self, stats: dict[str, any]) -> str:
        lines = [
            "📈 **WOCHEN-STATISTIK**",
            f"📅 Zeitraum: {stats['start_date']} - {stats['end_date']}",
            "",
        ]

        total_minutes = stats["total_minutes"]
        subject_minutes = stats["subject_minutes"]
        days_learned = stats.get("days_learned", 0)

        if total_minutes == 0:
            lines.append("🤷 Keine abgeschlossenen Lerneinheiten in diesem Zeitraum.")
            return "\n".join(lines)

        lines.append(f"⏱️ **Gesamtzeit:** {self.format_total_minutes(total_minutes)}")
        lines.append(f"📅 **Lerntage:** {days_learned}/{stats['days']}")
        lines.append("")

        if subject_minutes:
            lines.append("📚 **Nach Fächern:**")
            sorted_subjects = sorted(subject_minutes.items(), key=lambda x: x[1], reverse=True)
            for subject, minutes in sorted_subjects:
                sc = self.config.get_subject_by_name(subject)
                emoji = sc.emoji if sc else "📘"
                dur = self.format_total_minutes(minutes)
                pct = (minutes / total_minutes * 100) if total_minutes > 0 else 0
                bar_len = int(pct / 10)
                bar = "█" * bar_len + "░" * (10 - bar_len)
                lines.append(f"{emoji} **{subject}**")
                lines.append(f"   {bar} {dur} ({pct:.0f}%)")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Fun / random
    # ------------------------------------------------------------------

    def get_funny_error(self) -> str:
        messages = [
            "🤔 Das hat nicht geklappt! Selbst ein Einhorn wäre verwirrt...",
            "🦄 Ups! Das war wohl nichts. Versuch's nochmal, du schaffst das!",
            "😅 Oh nein! Das ging schief wie ein Pingpong-Ball im Tornado!",
            "🚀 Houston, wir haben ein Problem! (Aber es ist lösbar!)",
            "🎪 Das war eine interessante Eingabe, aber der Bot ist verwirrt!",
        ]
        return choice(messages)

    def get_funny_number_error(self) -> str:
        lo, hi = self.config.min_minutes, self.config.max_minutes
        messages = [
            f"🔢 Diese Zahl ist mir zu mystisch! Ich brauche was zwischen {lo} und {hi}.",
            f"🎯 Knapp daneben! Zahlen zwischen {lo} und {hi} sind perfekt!",
            f"🚀 Diese Zahl ist zu weit weg! Bleib zwischen {lo} und {hi}.",
        ]
        return choice(messages)

    def get_random_happy_image(self) -> str:
        return choice(self.config.horse_happy_images)

    def get_random_sad_gif(self) -> str:
        return choice(self.config.sad_gifs)
