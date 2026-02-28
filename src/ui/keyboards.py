"""UI components for keyboards and menus."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from core.config import BotConfig
from models.settings import WEEKDAYS


class KeyboardBuilder:
    """Builder for Telegram keyboards."""

    def __init__(self, config: BotConfig):
        self.config = config

    def get_main_keyboard(self) -> ReplyKeyboardMarkup:
        """Build the main reply keyboard with menu button."""
        return ReplyKeyboardMarkup(
            [["📋 Menü"]], resize_keyboard=True, one_time_keyboard=False, selective=True
        )

    def build_main_menu(self) -> InlineKeyboardMarkup:
        """Build the main inline menu."""
        kb = [
            [InlineKeyboardButton("📅 Wochenplan bearbeiten", callback_data="menu_plan")],
            [InlineKeyboardButton("📊 Wochenübersicht", callback_data="menu_overview")],
            [InlineKeyboardButton("⏰ Zeiten verwalten", callback_data="menu_times")],
            [InlineKeyboardButton("📌 Heute anzeigen", callback_data="menu_today")],
            [InlineKeyboardButton("📈 Wochen-Statistik", callback_data="menu_weekly_stats")],
            [InlineKeyboardButton("🔄 Schließen", callback_data="menu_close")],
        ]
        return InlineKeyboardMarkup(kb)

    # ------------------------------------------------------------------
    # Weekday / subject / minutes menus
    # ------------------------------------------------------------------

    def build_weekday_menu(self) -> InlineKeyboardMarkup:
        row1 = [
            InlineKeyboardButton(wd.capitalize(), callback_data=f"plan_day_{wd}")
            for wd in WEEKDAYS[:4]
        ]
        row2 = [
            InlineKeyboardButton(wd.capitalize(), callback_data=f"plan_day_{wd}")
            for wd in WEEKDAYS[4:]
        ]
        back = [InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main")]
        return InlineKeyboardMarkup([row1, row2, back])

    def build_subject_menu(self, weekday: str) -> InlineKeyboardMarkup:
        buttons = []
        for sc in self.config.allowed_subjects:
            buttons.append(
                InlineKeyboardButton(
                    f"{sc.emoji} {sc.name}", callback_data=f"plan_subject_{weekday}_{sc.name}"
                )
            )
        rows = [buttons[i: i + 2] for i in range(0, len(buttons), 2)]
        rows.append([InlineKeyboardButton("⬅️ Tage", callback_data="plan_days")])
        return InlineKeyboardMarkup(rows)

    def build_minutes_menu(self, weekday: str, subject: str) -> InlineKeyboardMarkup:
        rows: list[list[InlineKeyboardButton]] = []
        row: list[InlineKeyboardButton] = []
        for m in self.config.duration_choices:
            row.append(
                InlineKeyboardButton(
                    str(m), callback_data=f"plan_minutes_{weekday}_{subject}_{m}"
                )
            )
            if len(row) == 4:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append(
            [InlineKeyboardButton(
                "Andere", callback_data=f"plan_minutes_custom_{weekday}_{subject}"
            )]
        )
        rows.append([InlineKeyboardButton("⬅️ Fach", callback_data=f"plan_day_{weekday}")])
        return InlineKeyboardMarkup(rows)

    # ------------------------------------------------------------------
    # Morning planning
    # ------------------------------------------------------------------

    def build_morning_planning_keyboard(self, jokers_left: int) -> InlineKeyboardMarkup:
        subject_buttons = []
        for sc in self.config.allowed_subjects[:2]:
            subject_buttons.append(
                InlineKeyboardButton(
                    f"{sc.emoji} {sc.name}", callback_data=f"plan_subject_{sc.name}"
                )
            )
        joker_button = [
            InlineKeyboardButton(
                f"🏖️ Joker ({max(0, jokers_left)} übrig)", callback_data="use_joker"
            )
        ]
        return InlineKeyboardMarkup([subject_buttons, joker_button])

    def build_dynamic_time_menu(self, subject: str) -> InlineKeyboardMarkup:
        rows: list[list[InlineKeyboardButton]] = []
        row: list[InlineKeyboardButton] = []
        for option in self.config.dynamic_planning_times:
            row.append(InlineKeyboardButton(option, callback_data=f"plan_time_{option}"))
            if len(row) == 3:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append(
            [InlineKeyboardButton(f"⬅️ {subject} ändern", callback_data="morning_subjects")]
        )
        return InlineKeyboardMarkup(rows)

    # ------------------------------------------------------------------
    # Reminder time management
    # ------------------------------------------------------------------

    def build_times_menu(self, reminder_times: list[str]) -> InlineKeyboardMarkup:
        """Build the reminder-times overview menu."""
        rows: list[list[InlineKeyboardButton]] = []

        if reminder_times:
            for t in sorted(reminder_times):
                rows.append([
                    InlineKeyboardButton(f"⏰ {t}", callback_data="noop"),
                    InlineKeyboardButton("🗑️", callback_data=f"del_time_{t}"),
                ])
        else:
            rows.append([InlineKeyboardButton("— Keine Zeiten —", callback_data="noop")])

        rows.append([InlineKeyboardButton("➕ Zeit hinzufügen", callback_data="add_time")])
        rows.append([InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main")])
        return InlineKeyboardMarkup(rows)

    def build_hour_picker(self) -> InlineKeyboardMarkup:
        """Build hour-selection grid (0-23)."""
        rows: list[list[InlineKeyboardButton]] = []
        row: list[InlineKeyboardButton] = []
        for h in range(24):
            row.append(
                InlineKeyboardButton(f"{h:02d}", callback_data=f"pick_hour_{h:02d}")
            )
            if len(row) == 6:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("⬅️ Abbrechen", callback_data="menu_times")])
        return InlineKeyboardMarkup(rows)

    def build_minute_picker(self, hour: str) -> InlineKeyboardMarkup:
        """Build minute-selection grid for a given hour."""
        rows: list[list[InlineKeyboardButton]] = []
        row: list[InlineKeyboardButton] = []
        for m in (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55):
            row.append(
                InlineKeyboardButton(
                    f"{hour}:{m:02d}", callback_data=f"pick_minute_{hour}_{m:02d}"
                )
            )
            if len(row) == 4:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("⬅️ Stunde ändern", callback_data="add_time")])
        return InlineKeyboardMarkup(rows)

    # ------------------------------------------------------------------
    # Overview menu
    # ------------------------------------------------------------------

    def build_overview_menu(self, week_plan: dict) -> InlineKeyboardMarkup:
        buttons: list[list[InlineKeyboardButton]] = []
        emoji_map = {
            "montag": "🟦", "dienstag": "🟩", "mittwoch": "🟨",
            "donnerstag": "🟧", "freitag": "🟪", "samstag": "🟫", "sonntag": "⬜",
        }
        day_buttons: list[InlineKeyboardButton] = []
        for weekday in WEEKDAYS[:4]:
            emoji = emoji_map.get(weekday, "•")
            if weekday in week_plan:
                day_buttons.append(
                    InlineKeyboardButton(
                        f"{emoji} {weekday[:2].upper()}", callback_data=f"plan_day_{weekday}"
                    )
                )
            else:
                day_buttons.append(
                    InlineKeyboardButton(
                        f"➕ {weekday[:2].upper()}", callback_data=f"plan_day_{weekday}"
                    )
                )
        if day_buttons:
            buttons.append(day_buttons)

        day_buttons = []
        for weekday in WEEKDAYS[4:]:
            emoji = emoji_map.get(weekday, "•")
            if weekday in week_plan:
                day_buttons.append(
                    InlineKeyboardButton(
                        f"{emoji} {weekday[:2].upper()}", callback_data=f"plan_day_{weekday}"
                    )
                )
            else:
                day_buttons.append(
                    InlineKeyboardButton(
                        f"➕ {weekday[:2].upper()}", callback_data=f"plan_day_{weekday}"
                    )
                )
        if day_buttons:
            buttons.append(day_buttons)

        buttons.append([InlineKeyboardButton("📅 Wochenplan", callback_data="menu_plan")])
        buttons.append([
            InlineKeyboardButton("🔄 Aktualisieren", callback_data="menu_overview"),
            InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main"),
        ])
        return InlineKeyboardMarkup(buttons)

    # ------------------------------------------------------------------
    # Daily check / response
    # ------------------------------------------------------------------

    def build_learned_response_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Ja ✅", callback_data="learned_yes"),
                InlineKeyboardButton("Nein ❌", callback_data="learned_no"),
            ]
        ])

    def build_skip_comment_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Überspringen ⏭️", callback_data="skip_comment")]
        ])
