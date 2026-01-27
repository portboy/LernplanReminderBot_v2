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
            [InlineKeyboardButton("🔄 Schließen", callback_data="menu_close")],
        ]
        return InlineKeyboardMarkup(kb)

    def build_weekday_menu(self) -> InlineKeyboardMarkup:
        """Build weekday selection menu."""
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
        """Build subject selection menu for a specific weekday."""
        buttons = []
        for subject_config in self.config.allowed_subjects:
            emoji = subject_config.emoji
            name = subject_config.name
            buttons.append(
                InlineKeyboardButton(
                    f"{emoji} {name}", callback_data=f"plan_subject_{weekday}_{name}"
                )
            )
        
        # Split into rows of 2
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        rows.append([InlineKeyboardButton("⬅️ Tage", callback_data="plan_days")])
        return InlineKeyboardMarkup(rows)

    def build_minutes_menu(self, weekday: str, subject: str) -> InlineKeyboardMarkup:
        """Build minutes selection menu."""
        rows = []
        row = []
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
            [
                InlineKeyboardButton(
                    "Andere", callback_data=f"plan_minutes_custom_{weekday}_{subject}"
                )
            ]
        )
        rows.append([InlineKeyboardButton("⬅️ Fach", callback_data=f"plan_day_{weekday}")])
        return InlineKeyboardMarkup(rows)

    def build_morning_planning_keyboard(self, jokers_left: int) -> InlineKeyboardMarkup:
        """Build the morning planning keyboard with subjects and joker."""
        # Get first 2 subjects for quick access
        subject_buttons = []
        for subject_config in self.config.allowed_subjects[:2]:
            emoji = subject_config.emoji
            name = subject_config.name
            subject_buttons.append(
                InlineKeyboardButton(f"{emoji} {name}", callback_data=f"plan_subject_{name}")
            )
        
        joker_button = [
            InlineKeyboardButton(
                f"🏖️ Joker ({max(0, jokers_left)} übrig)", callback_data="use_joker"
            )
        ]
        
        return InlineKeyboardMarkup([subject_buttons, joker_button])

    def build_dynamic_time_menu(self, subject: str) -> InlineKeyboardMarkup:
        """Build time selection menu for dynamic day planning."""
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

    def build_overview_menu(self, week_plan: dict) -> InlineKeyboardMarkup:
        """Build an interactive menu for the weekly overview."""
        buttons = []

        # Day editing buttons (only for days with plans)
        day_buttons = []
        emoji_map = {
            "montag": "🟦",
            "dienstag": "🟩",
            "mittwoch": "🟨",
            "donnerstag": "🟧",
            "freitag": "🟪",
            "samstag": "🟫",
            "sonntag": "⬜",
        }
        
        for weekday in WEEKDAYS[:4]:  # Mon-Thu
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

        # Fri-Sun
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

        # Quick actions
        buttons.append([InlineKeyboardButton("📅 Wochenplan", callback_data="menu_plan")])

        # Refresh and back
        control_buttons = [
            InlineKeyboardButton("🔄 Aktualisieren", callback_data="menu_overview"),
            InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main"),
        ]
        buttons.append(control_buttons)

        return InlineKeyboardMarkup(buttons)

    def build_learned_response_keyboard(self) -> InlineKeyboardMarkup:
        """Build yes/no keyboard for daily check."""
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Ja ✅", callback_data="learned_yes"),
                    InlineKeyboardButton("Nein ❌", callback_data="learned_no"),
                ]
            ]
        )
