from __future__ import annotations

import logging
import os
from datetime import datetime, time, timezone
from pathlib import Path
from random import choice
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.logging_config import setup_logging
from models.settings import WEEKDAYS, DayPlan, SettingsRepository, UserSettings

LOGGER = logging.getLogger(__name__)

HORSE_HAPPY_IMAGES = [
    "https://images.pexels.com/photos/1996333/pexels-photo-1996333.jpeg",
    "https://images.pexels.com/photos/52500/horse-herd-fog-nature-52500.jpeg",
    "https://images.pexels.com/photos/2749423/pexels-photo-2749423.jpeg",
]
SAD_GIFS = [
    "https://media.giphy.com/media/3oz8xKaR836UJOYeOc/giphy.gif",
    "https://media.giphy.com/media/l3vR9O6r8n6u7q1lS/giphy.gif",
    "https://media.giphy.com/media/9Y5BbDSkSTiY8/giphy.gif",
]

FUNNY_ERROR_MESSAGES = [
    "🤔 Das hat nicht geklappt! Selbst ein Einhorn wäre verwirrt...",
    "🦄 Ups! Das war wohl nichts. Versuch's nochmal, du schaffst das!",
    "😅 Oh nein! Das ging schief wie ein Pingpong-Ball im Tornado!",
    "🎭 Autsch! Das war ein kreativer Versuch, aber leider daneben...",
    "🚀 Houston, wir haben ein Problem! (Aber es ist lösbar!)",
    "🎪 Das war eine interessante Eingabe, aber der Bot ist verwirrt!",
    "🎨 Kreativ, aber leider nicht das, was ich erwartet habe!",
    "🎪 Abrakadabra... och, der Zauber hat nicht funktioniert!",
]

FUNNY_NUMBER_ERRORS = [
    "🔢 Diese Zahl ist mir zu mystisch! Ich brauche was zwischen 1 und 180.",
    "🎯 Knapp daneben! Zahlen zwischen 1 und 180 sind perfekt!",
    "🎪 Diese Zahl ist außerhalb meines Universums! 1-180 bitte!",
    "🚀 Diese Zahl ist zu weit weg! Bleib zwischen 1 und 180.",
]

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = REPO_ROOT / DATA_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)

repo = SettingsRepository(DATA_DIR)


def _parse_chat_id(env_name: str) -> int | None:
    value = os.getenv(env_name)
    if not value:
        return None
    try:
        return int(value.strip())
    except ValueError:
        LOGGER.warning("Invalid chat id for %s: %s", env_name, value)
        return None


STUDENT_CHAT_ID = _parse_chat_id("STUDENT_CHAT_ID")
PARENT_CHAT_ID = _parse_chat_id("PARENT_CHAT_ID")


def _load_timezone() -> timezone | ZoneInfo:
    tz_name = os.getenv("TIMEZONE", "Europe/Berlin")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        LOGGER.warning("Unknown timezone '%s', falling back to UTC", tz_name)
        return timezone.utc


TIMEZONE = _load_timezone()


ALLOWED_SUBJECTS = ["Mathe", "Englisch"]
DYNAMIC_PLANNING_TIMES = ["07:30", "09:00", "14:00", "16:30", "18:30", "20:30"]
DURATION_CHOICES = [15, 30, 45, 60, 90, 120]
MIN_MINUTES = 1
MAX_MINUTES = 180
DAY_OVERVIEW_ICONS = {
    "montag": "🔵",
    "dienstag": "🟢",
    "mittwoch": "🟡",
    "donnerstag": "🟠",
    "freitag": "🟣",
    "samstag": "🟤",
    "sonntag": "⚪",
}


def get_shared_chat_ids() -> list[int]:
    ids: list[int] = []
    if STUDENT_CHAT_ID:
        ids.append(STUDENT_CHAT_ID)
    if PARENT_CHAT_ID and PARENT_CHAT_ID not in ids:
        ids.append(PARENT_CHAT_ID)
    return ids


def get_shared_reminder_times() -> list[str]:
    for candidate in (STUDENT_CHAT_ID, PARENT_CHAT_ID):
        if candidate is None:
            continue
        settings = repo.load(candidate)
        if settings.reminder_times:
            return list(settings.reminder_times)
    return []


def _clone_week_plan(plan: dict[str, DayPlan]) -> dict[str, DayPlan]:
    return {
        day: DayPlan(subject=value.subject, minutes=value.minutes) for day, value in plan.items()
    }


def get_shared_week_plan() -> dict[str, DayPlan]:
    for candidate in (STUDENT_CHAT_ID, PARENT_CHAT_ID):
        if candidate is None:
            continue
        settings = repo.load(candidate)
        if settings.week_plan:
            return _clone_week_plan(settings.week_plan)
    return {}


def sync_reminder_times(new_times: list[str]) -> None:
    shared_ids = get_shared_chat_ids()
    if not shared_ids:
        return
    normalized = list(new_times)
    for chat_id in shared_ids:
        settings = repo.load(chat_id)
        settings.reminder_times = normalized
        repo.save(settings)


def sync_week_plan(new_plan: dict[str, DayPlan]) -> None:
    plan = _clone_week_plan(new_plan) if new_plan else {}
    shared_ids = get_shared_chat_ids()
    if not shared_ids:
        return
    for chat_id in shared_ids:
        settings = repo.load(chat_id)
        settings.week_plan = _clone_week_plan(plan)
        repo.save(settings)


def _format_duration(minutes: int) -> str:
    if minutes <= 0:
        return "0min"
    hours, remainder = divmod(minutes, 60)
    fragments: list[str] = []
    if hours:
        fragments.append(f"{hours}h")
    if remainder:
        fragments.append(f"{remainder}min")
    return " ".join(fragments) if fragments else "0min"


def _format_total_minutes(minutes: int) -> str:
    if minutes <= 0:
        return "0 Minuten"
    return _format_duration(minutes)


def _reminder_time_icon(time_str: str) -> str:
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


def build_reminder_message(settings: UserSettings) -> str:
    """Build a reminder message for the current day."""
    now_dt = datetime.now(TIMEZONE)
    today = WEEKDAYS[now_dt.weekday()]
    today_iso = now_dt.date().isoformat()
    lines = [f"📌 Erinnerung für {today.capitalize()}"]

    day_plan = settings.week_plan.get(today)
    if day_plan:
        duration = _format_duration(day_plan.minutes)
        lines.append(f"📘 {day_plan.subject} ({duration})")
    else:
        lines.append("📘 Keine feste Aufgabe hinterlegt.")

    dynamic_entries = [
        entry for entry in settings.daily_dynamic_plan if entry.get("date_iso") == today_iso
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


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["📋 Menü"]], resize_keyboard=True, one_time_keyboard=False, selective=True
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    repo.load(chat_id)
    await update.message.reply_text(
        "Willkommen beim Lernplan Reminder Bot! Nutze den Menü-Button oder /menu.",
        reply_markup=get_main_keyboard(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Nutze /menu für das Hauptmenü, /plan für den Wochenplan und /heute für die Übersicht.",
        reply_markup=get_main_keyboard(),
    )


async def plan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text("Wochentage wählen:", reply_markup=build_weekday_menu())


async def heute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    overview_text = build_weekly_overview(chat_id)
    await update.message.reply_text(overview_text)


def build_main_menu() -> InlineKeyboardMarkup:
    """Build the main inline menu."""
    kb = [
        [InlineKeyboardButton("📅 Wochenplan bearbeiten", callback_data="menu_plan")],
        [InlineKeyboardButton("📊 Wochenübersicht", callback_data="menu_overview")],
        [InlineKeyboardButton("🔄 Schließen", callback_data="menu_close")],
    ]
    return InlineKeyboardMarkup(kb)


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text("Hauptmenü:", reply_markup=build_main_menu())


def build_weekday_menu() -> InlineKeyboardMarkup:
    """Build weekday selection menu."""
    row1 = [
        InlineKeyboardButton(wd.capitalize(), callback_data=f"plan_day_{wd}") for wd in WEEKDAYS[:4]
    ]
    row2 = [
        InlineKeyboardButton(wd.capitalize(), callback_data=f"plan_day_{wd}") for wd in WEEKDAYS[4:]
    ]
    back = [InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main")]
    return InlineKeyboardMarkup([row1, row2, back])


def build_dynamic_time_menu(subject: str) -> InlineKeyboardMarkup:
    """Build time selection menu for dynamic day planning."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for option in DYNAMIC_PLANNING_TIMES:
        row.append(InlineKeyboardButton(option, callback_data=f"plan_time_{option}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(f"⬅️ {subject} ändern", callback_data="morning_subjects")])
    return InlineKeyboardMarkup(rows)


def build_morning_planning_keyboard(jokers_left: int) -> InlineKeyboardMarkup:
    """Build the morning planning keyboard with static subjects and joker usage."""
    subject_buttons = [
        InlineKeyboardButton(subject, callback_data=f"plan_subject_{subject}")
        for subject in ALLOWED_SUBJECTS[:2]
    ]
    joker_button = [
        InlineKeyboardButton(f"🏖️ Joker ({max(0, jokers_left)} übrig)", callback_data="use_joker")
    ]
    return InlineKeyboardMarkup([subject_buttons, joker_button])


def build_subject_menu(weekday: str) -> InlineKeyboardMarkup:
    """Build subject selection menu for a specific weekday."""
    buttons = [
        InlineKeyboardButton("Mathe", callback_data=f"plan_subject_{weekday}_Mathe"),
        InlineKeyboardButton("Englisch", callback_data=f"plan_subject_{weekday}_Englisch"),
    ]
    back = [InlineKeyboardButton("⬅️ Tage", callback_data="plan_days")]
    return InlineKeyboardMarkup([buttons, back])


def build_weekly_overview(chat_id: int) -> str:
    """Build a professional weekly overview with formatted table."""
    # Use shared plan if this is a parent or student chat, otherwise use individual settings
    if chat_id in get_shared_chat_ids():
        week_plan = get_shared_week_plan()
        reminder_times = get_shared_reminder_times()
    else:
        settings = repo.load(chat_id)
        week_plan = settings.week_plan
        reminder_times = settings.reminder_times

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
            duration = _format_duration(plan.minutes)
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
    overview_lines.append(f"Gesamtzeit: {_format_total_minutes(total_minutes)}")
    overview_lines.append("")
    overview_lines.append("📌 Tagesfarben:")
    overview_lines.append(
        " ".join(f"{DAY_OVERVIEW_ICONS.get(day, '•')} {day[:2].upper()}" for day in WEEKDAYS)
    )
    overview_lines.append("")
    overview_lines.append("⏰ **ERINNERUNGSZEITEN**")

    if reminder_times:
        for reminder in sorted(reminder_times):
            overview_lines.append(f"{_reminder_time_icon(reminder)} **{reminder}**")
    else:
        overview_lines.append("Keine Erinnerungszeiten")

    return "\n".join(overview_lines)


def build_overview_menu(chat_id: int) -> InlineKeyboardMarkup:
    """Build an interactive menu for the weekly overview with quick actions."""
    # Use shared plan if this is a parent or student chat, otherwise use individual settings
    if chat_id in get_shared_chat_ids():
        week_plan = get_shared_week_plan()
    else:
        settings = repo.load(chat_id)
        week_plan = settings.week_plan

    buttons = []

    # Row 1: Quick day editing buttons (only for days with plans)
    day_buttons = []
    for weekday in WEEKDAYS[:4]:  # Mon-Thu
        emoji_map = {"montag": "🟦", "dienstag": "🟩", "mittwoch": "🟨", "donnerstag": "🟧"}
        if weekday in week_plan:
            emoji = emoji_map[weekday]
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

    # Row 2: Fri-Sun
    day_buttons = []
    for weekday in WEEKDAYS[4:]:  # Fri-Sun
        if weekday in week_plan:
            emoji = {"freitag": "🟪", "samstag": "🟫", "sonntag": "⬜"}[weekday]
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

    # Row 3: Quick actions
    quick_actions = [InlineKeyboardButton("📅 Wochenplan", callback_data="menu_plan")]
    buttons.append(quick_actions)

    # Row 4: Refresh and back
    control_buttons = [
        InlineKeyboardButton("🔄 Aktualisieren", callback_data="menu_overview"),
        InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main"),
    ]
    buttons.append(control_buttons)

    return InlineKeyboardMarkup(buttons)


def build_minutes_menu(weekday: str, subject: str) -> InlineKeyboardMarkup:
    """Build minutes selection menu."""
    rows = []
    row = []
    for m in DURATION_CHOICES:
        row.append(
            InlineKeyboardButton(str(m), callback_data=f"plan_minutes_{weekday}_{subject}_{m}")
        )
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [InlineKeyboardButton("Andere", callback_data=f"plan_minutes_custom_{weekday}_{subject}")]
    )
    rows.append([InlineKeyboardButton("⬅️ Fach", callback_data=f"plan_day_{weekday}")])
    return InlineKeyboardMarkup(rows)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    chat_id = query.message.chat_id
    settings = repo.load(chat_id)

    if data == "morning_subjects":
        jokers_left = max(0, settings.jokers_available)
        await query.edit_message_text(
            "Guten Morgen! ☀️ Plan für heute?",
            reply_markup=build_morning_planning_keyboard(jokers_left),
        )
        await query.answer()
        return
    if data.startswith("plan_subject_"):
        parts = data.split("_")
        if len(parts) == 3:
            subject = parts[2]
            context.user_data["dynamic_subject"] = subject
            await query.edit_message_text(
                f"Welche Zeit passt für {subject}?",
                reply_markup=build_dynamic_time_menu(subject),
            )
            await query.answer()
            return
    if data.startswith("plan_time_"):
        time_str = data.removeprefix("plan_time_")
        subject = context.user_data.get("dynamic_subject")
        if not subject:
            await query.answer("Bitte zuerst ein Fach wählen.", show_alert=True)
            return
        try:
            hh, mm = map(int, time_str.split(":"))
            selected_time = time(hour=hh, minute=mm)
        except (ValueError, AttributeError):
            await query.answer("Ungültige Zeit.", show_alert=True)
            return

        now_dt = datetime.now(TIMEZONE)
        target_dt = datetime.combine(now_dt.date(), selected_time, tzinfo=TIMEZONE)
        if target_dt <= now_dt:
            await query.answer("Diese Zeit ist bereits vorbei.", show_alert=True)
            return

        chat_id = query.message.chat_id
        settings = repo.load(chat_id)
        today_iso = now_dt.date().isoformat()
        todays_entries = [
            entry for entry in settings.daily_dynamic_plan if entry.get("date_iso") == today_iso
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
        repo.save(settings)

        scheduled = False
        if context.application:
            scheduled = schedule_dynamic_job(context.application, chat_id, subject, time_str)
        else:
            LOGGER.warning("plan_time: Missing application context for scheduling")

        confirmation = f"Geplant: {subject} um {time_str}. Ich erinnere dich rechtzeitig!"
        if not scheduled:
            confirmation = (
                f"{subject} um {time_str} gespeichert, aber Erinnerung konnte nicht geplant werden."
            )

        await query.edit_message_text(confirmation)
        await query.answer("Plan gespeichert!")
        context.user_data.pop("dynamic_subject", None)
        return
    if data == "use_joker":
        if settings.jokers_available <= 0:
            await query.answer("Keine Joker verfügbar.", show_alert=True)
            return
        settings.jokers_available -= 1
        repo.save(settings)
        await query.edit_message_text("Genieß den Tag! ☀️ Joker eingesetzt.")
        await query.answer("Joker genutzt!")
        return
    if data == "menu_main":
        await query.edit_message_text("Hauptmenü:", reply_markup=build_main_menu())
        await query.answer()
        return
    if data == "menu_plan" or data == "plan_days":
        await query.edit_message_text("Wochentage wählen:", reply_markup=build_weekday_menu())
        await query.answer()
        return
    if data == "menu_overview":
        overview_text = build_weekly_overview(chat_id)
        await query.edit_message_text(
            overview_text, reply_markup=build_overview_menu(chat_id), parse_mode="Markdown"
        )
        await query.answer()
        return
    if data == "menu_close":
        await query.edit_message_text("Menü geschlossen.")
        await query.answer()
        # Send a new message with the main keyboard to restore the menu button
        await query.message.reply_text(
            "Nutze den Menü-Button unten oder /menu.", reply_markup=get_main_keyboard()
        )
        return
    if data.startswith("plan_day_"):
        wd = data.removeprefix("plan_day_")
        context.user_data["plan_weekday"] = wd
        await query.edit_message_text(
            f"Fach für {wd.capitalize()} wählen:", reply_markup=build_subject_menu(wd)
        )
        await query.answer()
        return
    if data.startswith("plan_subject_"):
        parts = data.split("_", 3)
        weekday = parts[2]
        subject = parts[3]
        context.user_data["plan_subject"] = subject
        context.user_data["plan_weekday"] = weekday
        await query.edit_message_text(
            f"Minuten für {weekday.capitalize()} – {subject} wählen:",
            reply_markup=build_minutes_menu(weekday, subject),
        )
        await query.answer()
        return
    if data.startswith("plan_minutes_custom_"):
        _, _, _, weekday, subject = data.split("_", 4)
        context.user_data["awaiting_minutes"] = (weekday, subject)
        await query.edit_message_text(
            f"Eigene Minutenanzahl für {weekday.capitalize()} – {subject} eingeben (Zahl 1-180):"
        )
        await query.answer()
        return
    if data.startswith("plan_minutes_"):
        # plan_minutes_{weekday}_{subject}_{m}
        _, _, weekday, subject, minutes = data.split("_", 4)
        try:
            m = int(minutes)

            # Use shared plan if this is a parent or student chat
            if chat_id in get_shared_chat_ids():
                week_plan = get_shared_week_plan()
                week_plan[weekday] = DayPlan(subject=subject, minutes=m)
                sync_week_plan(week_plan)
            else:
                settings.week_plan[weekday] = DayPlan(subject=subject, minutes=m)
                repo.save(settings)

            schedule_all_reminders(context.application)
            await query.edit_message_text(
                f"Gespeichert: {weekday.capitalize()} – {subject} ({m} Minuten)",
                reply_markup=build_weekday_menu(),
            )
            await query.answer("Gespeichert")
        except (ValueError, KeyError) as e:
            LOGGER.error(f"Error saving plan minutes: {e}")
            await query.answer("🎪 Diese Minuten sind zu mystisch für mich!")
        return
    # Fallback für learned_yes/no handled in separate handler originally
    await query.answer()


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    settings = repo.load(chat_id)

    # Handle menu button
    if text == "📋 Menü":
        await update.message.reply_text("Hauptmenü:", reply_markup=build_main_menu())
        return

    if "awaiting_minutes" in context.user_data:
        weekday, subject = context.user_data.pop("awaiting_minutes")
        try:
            minutes_value = int(text)
            if not (MIN_MINUTES <= minutes_value <= MAX_MINUTES):
                raise ValueError("Minutes out of range")
        except (ValueError, AttributeError):
            await update.message.reply_text(choice(FUNNY_NUMBER_ERRORS))
            return

        if chat_id in get_shared_chat_ids():
            week_plan = get_shared_week_plan()
            week_plan[weekday] = DayPlan(subject=subject, minutes=minutes_value)
            sync_week_plan(week_plan)
        else:
            settings.week_plan[weekday] = DayPlan(subject=subject, minutes=minutes_value)
            repo.save(settings)

        schedule_all_reminders(context.application)
        await update.message.reply_text(
            f"Gespeichert: {weekday.capitalize()} – {subject} ({minutes_value} Minuten).",
            reply_markup=get_main_keyboard(),
        )
        return

    await update.message.reply_text(choice(FUNNY_ERROR_MESSAGES))


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.voice:
        return

    chat_id = message.chat_id
    if chat_id != STUDENT_CHAT_ID:
        return

    settings = repo.load(chat_id)
    forwarded = False
    if PARENT_CHAT_ID:
        try:
            caption = "🎙️ Sprachnachricht vom Schüler"
            await context.bot.send_voice(
                chat_id=PARENT_CHAT_ID,
                voice=message.voice.file_id,
                caption=caption,
            )
            forwarded = True
        except Exception as exc:
            LOGGER.error("handle_voice_message: Failed to forward voice message: %s", exc)

    now = datetime.now(TIMEZONE)
    today_iso = now.date().isoformat()
    now_time = now.time()

    past_candidate = None
    past_candidate_time = None
    fallback_candidate = None
    fallback_candidate_time = None

    for entry in settings.daily_dynamic_plan:
        if entry.get("date_iso") != today_iso or entry.get("completed"):
            continue
        time_str = entry.get("time_str")
        try:
            hh, mm = map(int, (time_str or "").split(":"))
            entry_time = time(hour=hh, minute=mm)
        except (ValueError, TypeError):
            continue

        if entry_time <= now_time:
            if past_candidate_time is None or entry_time < past_candidate_time:
                past_candidate = entry
                past_candidate_time = entry_time
        if fallback_candidate_time is None or entry_time < fallback_candidate_time:
            fallback_candidate = entry
            fallback_candidate_time = entry_time

    target_entry = past_candidate or fallback_candidate
    if target_entry:
        target_entry["completed"] = True
        repo.save(settings)

    if forwarded:
        await message.reply_text("✅ Nachricht weitergeleitet und Plan aktualisiert.")
    else:
        await message.reply_text("✅ Plan aktualisiert.")


async def test_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    settings = repo.load(chat_id)
    await update.message.reply_text(build_reminder_message(settings))


async def test_daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test command to manually trigger the daily check for debugging."""
    if not update.message:
        return
    await update.message.reply_text("🧪 Testing daily check function...")
    try:
        await daily_check(context)
        await update.message.reply_text("✅ Daily check function executed successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Daily check failed: {e}")
        LOGGER.error(f"test_daily_cmd: Error testing daily check: {e}", exc_info=True)


async def morning_planning_prompt(context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.info("morning_planning_prompt: Starting 07:30 morning prompt")

    if not STUDENT_CHAT_ID:
        LOGGER.warning(
            "morning_planning_prompt: STUDENT_CHAT_ID not set - skipping morning planning prompt"
        )
        return

    try:
        settings = repo.load(STUDENT_CHAT_ID)
        jokers_left = max(0, settings.jokers_available)
        keyboard = build_morning_planning_keyboard(jokers_left)

        await context.bot.send_message(
            chat_id=STUDENT_CHAT_ID,
            text="Guten Morgen! ☀️ Plan für heute?",
            reply_markup=keyboard,
        )
        LOGGER.info(
            f"morning_planning_prompt: Prompt sent to student chat {STUDENT_CHAT_ID} "
            f"(jokers={jokers_left})"
        )
    except Exception as e:
        LOGGER.error(f"morning_planning_prompt: Failed to send prompt: {e}", exc_info=True)


async def daily_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.info("daily_check: Starting 20:00 daily check")

    if not STUDENT_CHAT_ID:
        LOGGER.warning("daily_check: STUDENT_CHAT_ID not set - skipping daily check")
        return

    LOGGER.info(f"daily_check: Sending question to student chat {STUDENT_CHAT_ID}")

    try:
        settings = repo.load(STUDENT_CHAT_ID)
        now_dt = datetime.now(TIMEZONE)
        today = WEEKDAYS[now_dt.weekday()]
        today_iso = now_dt.date().isoformat()
        todays_entries = [
            entry for entry in settings.daily_dynamic_plan if entry.get("date_iso") == today_iso
        ]

        def _plan_sort_key(entry: dict) -> int:
            time_str = entry.get("time_str") or ""
            try:
                hh, mm = map(int, time_str.split(":"))
                return hh * 60 + mm
            except (ValueError, TypeError):
                return 24 * 60 + 1

        todays_entries_sorted = sorted(todays_entries, key=_plan_sort_key)
        completed_count = sum(1 for entry in todays_entries_sorted if entry.get("completed"))
        report_lines = [
            "📋 Tagesreport – Dynamische Planung",
            f"Datum: {now_dt.strftime('%d.%m.%Y')}",
        ]
        if todays_entries_sorted:
            for entry in todays_entries_sorted:
                status = "✅" if entry.get("completed") else "⬜"
                subject = entry.get("subject", "Unbekannt")
                time_str = entry.get("time_str", "--:--")
                report_lines.append(f"{status} {time_str} – {subject}")
        else:
            report_lines.append("Keine spontanen Lernpläne für heute hinterlegt.")
        report_lines.append(f"Erledigt: {completed_count}/{len(todays_entries_sorted)}")
        report_text = "\n".join(report_lines)

        dp = settings.week_plan.get(today)
        if dp:
            text = "Hast du heute auch gelernt?"
        else:
            text = "Heute war kein Lernplan-Eintrag hinterlegt – hast du trotzdem gelernt?"

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Ja ✅", callback_data="learned_yes"),
                    InlineKeyboardButton("Nein ❌", callback_data="learned_no"),
                ]
            ]
        )

        await context.bot.send_message(chat_id=STUDENT_CHAT_ID, text=text, reply_markup=kb)
        LOGGER.info(f"daily_check: Successfully sent question to student {STUDENT_CHAT_ID}")

        if PARENT_CHAT_ID and PARENT_CHAT_ID != STUDENT_CHAT_ID:
            await context.bot.send_message(
                chat_id=PARENT_CHAT_ID, text="(Info) 20-Uhr-Abfrage an Schüler gesendet."
            )
            LOGGER.info(f"daily_check: Successfully sent info to parent {PARENT_CHAT_ID}")
        elif not PARENT_CHAT_ID:
            LOGGER.info("daily_check: No parent notification (PARENT_CHAT_ID not set)")
        else:
            LOGGER.info(
                "daily_check: Parent chat equals student chat – "
                "skipping duplicate info notification"
            )

        if PARENT_CHAT_ID:
            await context.bot.send_message(chat_id=PARENT_CHAT_ID, text=report_text)
            LOGGER.info("daily_check: Sent dynamic plan report to parent")

        settings.daily_dynamic_plan = []
        repo.save(settings)
        LOGGER.info("daily_check: Cleared dynamic plan entries for next day")

    except Exception as e:
        LOGGER.error(f"daily_check: Error during daily check: {e}", exc_info=True)


async def dynamic_plan_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data or {}
    chat_id = job_data.get("chat_id")
    subject = job_data.get("subject")
    time_str = job_data.get("time_str")
    if not chat_id or not subject or not time_str:
        LOGGER.warning("dynamic_plan_job: Missing job data %s", job_data)
        return

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔔 Zeit für {subject} um {time_str}! Viel Erfolg!",
        )
    finally:
        settings = repo.load(chat_id)
        today_iso = datetime.now(TIMEZONE).date().isoformat()
        updated = False
        for entry in settings.daily_dynamic_plan:
            entry_date = entry.get("date_iso")
            if (
                entry.get("subject") == subject
                and entry.get("time_str") == time_str
                and entry.get("completed") is False
                and entry_date == today_iso
            ):
                entry["completed"] = True
                updated = True
                break
        if updated:
            repo.save(settings)


def schedule_dynamic_job(app: Application, chat_id: int, subject: str, time_str: str) -> bool:
    try:
        hh, mm = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        LOGGER.warning(
            "schedule_dynamic_job: Invalid time string '%s' for chat %s", time_str, chat_id
        )
        return False

    now_dt = datetime.now(TIMEZONE)
    target_dt = datetime.combine(now_dt.date(), time(hour=hh, minute=mm), tzinfo=TIMEZONE)
    if target_dt <= now_dt:
        LOGGER.info("schedule_dynamic_job: Skipping past time %s for chat %s", time_str, chat_id)
        return False

    safe_subject = abs(hash(subject)) % 10000
    job_name = f"dynamic_{chat_id}_{hh:02d}{mm:02d}_{safe_subject}"
    for job in app.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()

    app.job_queue.run_once(
        dynamic_plan_job,
        when=target_dt,
        name=job_name,
        data={"chat_id": chat_id, "subject": subject, "time_str": time_str},
    )
    LOGGER.info("schedule_dynamic_job: Scheduled %s for chat %s at %s", subject, chat_id, time_str)
    return True


async def on_learned_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    LOGGER.info(
        f"on_learned_response: Received callback '{data}' from chat {query.message.chat_id}"
    )

    try:
        if data == "learned_yes":
            img = choice(HORSE_HAPPY_IMAGES)
            await query.edit_message_text("Super! Weiter so! 🐴🎉")
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=img)
            LOGGER.info(
                f"on_learned_response: Sent positive response to chat {query.message.chat_id}"
            )

            if PARENT_CHAT_ID and PARENT_CHAT_ID != query.message.chat_id:
                await context.bot.send_message(
                    chat_id=PARENT_CHAT_ID, text="Antwort Schüler: JA gelernt ✅"
                )
                LOGGER.info(
                    f"on_learned_response: Sent 'YES' notification to parent {PARENT_CHAT_ID}"
                )
            else:
                LOGGER.info(
                    "on_learned_response: No parent notification for 'YES' "
                    "(not configured or same chat)"
                )

        elif data == "learned_no":
            gif = choice(SAD_GIFS)
            await query.edit_message_text("Vielleicht klappt es morgen besser. 🐴")
            await context.bot.send_animation(chat_id=query.message.chat_id, animation=gif)
            LOGGER.info(
                f"on_learned_response: Sent negative response to chat {query.message.chat_id}"
            )

            if PARENT_CHAT_ID and PARENT_CHAT_ID != query.message.chat_id:
                await context.bot.send_message(
                    chat_id=PARENT_CHAT_ID, text="Antwort Schüler: NEIN gelernt ❌"
                )
                LOGGER.info(
                    f"on_learned_response: Sent 'NO' notification to parent {PARENT_CHAT_ID}"
                )
            else:
                LOGGER.info(
                    "on_learned_response: No parent notification for 'NO' "
                    "(not configured or same chat)"
                )
        else:
            LOGGER.warning(f"on_learned_response: Unknown callback data '{data}'")

    except Exception as e:
        LOGGER.error(f"on_learned_response: Error handling callback '{data}': {e}", exc_info=True)


def schedule_all_reminders(app):
    LOGGER.info("schedule_all_reminders: Starting job scheduling")

    # Clear existing jobs
    job_count = len(app.job_queue.jobs())
    for job in app.job_queue.jobs():
        job.schedule_removal()
    LOGGER.info(f"schedule_all_reminders: Removed {job_count} existing jobs")

    dynamic_count = 0
    today = datetime.now(TIMEZONE)
    today_date = today.date()
    today_iso = today_date.isoformat()
    for uid in repo.list_user_ids():
        settings = repo.load(uid)
        # Dynamic day plans (only for current day)
        todays_entries = [
            entry for entry in settings.daily_dynamic_plan if entry.get("date_iso") == today_iso
        ]
        if len(todays_entries) != len(settings.daily_dynamic_plan):
            settings.daily_dynamic_plan = todays_entries
            repo.save(settings)

        for entry in todays_entries:
            if entry.get("completed"):
                continue
            subject = entry.get("subject")
            time_str = entry.get("time_str")
            if not subject or not time_str:
                continue
            try:
                hh, mm = map(int, time_str.split(":"))
            except (ValueError, AttributeError):
                LOGGER.warning(
                    "schedule_all_reminders: Invalid daily plan time '%s' for user %s",
                    time_str,
                    uid,
                )
                continue
            entry_dt = datetime.combine(today_date, time(hour=hh, minute=mm), tzinfo=TIMEZONE)
            if entry_dt <= today:
                continue
            if schedule_dynamic_job(app, uid, subject, time_str):
                dynamic_count += 1

    # 07:30 morning planning prompt
    app.job_queue.run_daily(
        morning_planning_prompt,
        time=time(hour=7, minute=30, tzinfo=TIMEZONE),
        name="morning_planning_prompt",
    )
    LOGGER.info("schedule_all_reminders: Scheduled morning_planning_prompt at 07:30")

    # 20:00 check
    app.job_queue.run_daily(
        daily_check,
        time=time(hour=20, minute=0, tzinfo=TIMEZONE),
        name="daily_check_20",
    )
    LOGGER.info("schedule_all_reminders: Scheduled daily_check at 20:00")

    # Log environment variables for debugging
    LOGGER.info(f"schedule_all_reminders: STUDENT_CHAT_ID = {STUDENT_CHAT_ID}")
    LOGGER.info(f"schedule_all_reminders: PARENT_CHAT_ID = {PARENT_CHAT_ID}")

    LOGGER.info(
        "schedule_all_reminders: Completed. Scheduled %s dynamic plans + "
        "morning planning + daily check",
        dynamic_count,
    )


def build_app():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN nicht gesetzt")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("plan", plan_cmd))
    app.add_handler(CommandHandler("heute", heute_cmd))
    app.add_handler(CommandHandler("test", test_cmd))
    app.add_handler(CommandHandler("testdaily", test_daily_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    # Callback Handler Reihenfolge: zuerst eigene Menüs, dann learned callbacks
    app.add_handler(CallbackQueryHandler(on_learned_response, pattern="^learned_"))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text))
    schedule_all_reminders(app)
    return app


def main():
    setup_logging()

    # Log configuration for debugging
    LOGGER.info("Bot starting...")
    LOGGER.info(
        f"Configuration: STUDENT_CHAT_ID={STUDENT_CHAT_ID}, PARENT_CHAT_ID={PARENT_CHAT_ID}"
    )

    # Warn if critical IDs are not set
    if not STUDENT_CHAT_ID:
        LOGGER.warning("STUDENT_CHAT_ID is not set - daily check will not work!")
    if not PARENT_CHAT_ID:
        LOGGER.warning("PARENT_CHAT_ID is not set - parent notifications will not work!")

    app = build_app()
    LOGGER.info("Bot startet ...")
    app.run_polling()


if __name__ == "__main__":
    main()
