import logging
import os
from datetime import datetime, time
from random import choice
from zoneinfo import ZoneInfo

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
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
TIMEZONE = ZoneInfo("Europe/Berlin")
DATA_DIR = os.getenv("DATA_DIR", "data")

repo = SettingsRepository(base_path=__import__("pathlib").Path(DATA_DIR))

MAX_REMINDERS = 3
MAX_MINUTES = 180
MIN_MINUTES = 1

REMINDER_EMOJIS = ["📚", "🧠", "✅", "✏️", "📖", "🦄", "🎯"]

PARENT_CHAT_ID = int(os.getenv("PARENT_CHAT_ID", "0"))  # optional Elternteil / Betreuer
STUDENT_CHAT_ID = int(os.getenv("STUDENT_CHAT_ID", "0"))  # für 20-Uhr Lern-Abfrage


def get_shared_chat_ids():
    """Get list of chat IDs that should share reminder times."""
    chat_ids = []
    if PARENT_CHAT_ID:
        chat_ids.append(PARENT_CHAT_ID)
    if STUDENT_CHAT_ID:
        chat_ids.append(STUDENT_CHAT_ID)
    return list(set(chat_ids))  # Remove duplicates if PARENT_CHAT_ID == STUDENT_CHAT_ID


def sync_reminder_times(new_times: list[str]):
    """Sync reminder times across all shared chat IDs."""
    for chat_id in get_shared_chat_ids():
        settings = repo.load(chat_id)
        settings.reminder_times = new_times.copy()
        repo.save(settings)


def get_shared_reminder_times():
    """Get the current shared reminder times (from student if available, otherwise parent)."""
    if STUDENT_CHAT_ID:
        return repo.load(STUDENT_CHAT_ID).reminder_times
    elif PARENT_CHAT_ID:
        return repo.load(PARENT_CHAT_ID).reminder_times
    return []


def sync_week_plan(new_plan: dict):
    """Sync weekly plan across all shared chat IDs."""
    for chat_id in get_shared_chat_ids():
        settings = repo.load(chat_id)
        settings.week_plan = new_plan.copy()
        repo.save(settings)


def get_shared_week_plan():
    """Get the current shared weekly plan (from student if available, otherwise parent)."""
    if STUDENT_CHAT_ID:
        return repo.load(STUDENT_CHAT_ID).week_plan
    elif PARENT_CHAT_ID:
        return repo.load(PARENT_CHAT_ID).week_plan
    return {}


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

FUNNY_TIME_ERRORS = [
    "⏰ Diese Zeit existiert nur in einer Parallelwelt! Format: HH:MM",
    "🕐 Hmm, ist das eine Geheimsprache? Ich verstehe nur HH:MM!",
    "⌚ Zeitreise fehlgeschlagen! Bitte im Format HH:MM eingeben.",
    "🕰️ Das war wohl keine Zeit, sondern ein Rätsel! Versuch HH:MM.",
]

FUNNY_NUMBER_ERRORS = [
    "🔢 Diese Zahl ist mir zu mystisch! Ich brauche was zwischen 1 und 180.",
    "🎯 Knapp daneben! Zahlen zwischen 1 und 180 sind perfekt!",
    "🎪 Diese Zahl ist außerhalb meines Universums! 1-180 bitte!",
    "🚀 Diese Zahl ist zu weit weg! Bleib zwischen 1 und 180.",
]


def build_reminder_message(settings: UserSettings) -> str:
    """Build a reminder message for the current day."""
    today = WEEKDAYS[datetime.now(TIMEZONE).weekday()]
    dp = settings.week_plan.get(today)
    emoji = choice(REMINDER_EMOJIS)
    if dp:
        return f"{emoji} Erinnerung: Heute {dp.minutes} Minuten {dp.subject} lernen!"
    return (
        f"{emoji} Erinnerung: Heute war kein Lernplan-Eintrag hinterlegt – "
        "trotzdem etwas lernen?"
    )


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Get the main keyboard with menu button."""
    keyboard = [[KeyboardButton("📋 Menü")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    settings = repo.load(chat_id)
    await update.message.reply_text(
        "Willkommen zum Lernplan Reminder Bot! "
        "Verwende den Menü-Button unten oder /help für Hilfe.",
        reply_markup=get_main_keyboard(),
    )
    # einfache Auto-Initialisierung falls kein Plan vorhanden
    if not settings.week_plan:
        # default simpler Plan: Mathe/Englisch Wechsel
        defaults = ["Mathe", "Englisch"]
        for idx, wd in enumerate(WEEKDAYS[:5]):  # nur Werktage vorinitialisieren
            settings.week_plan[wd] = DayPlan(subject=defaults[idx % 2], minutes=30)
        repo.save(settings)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "/start - Startet den Bot\n"
        "/help - Diese Hilfe\n"
        "/plan - Zeigt den Wochenplan\n"
        "/zeiten - Zeigt Erinnerungszeiten\n"
        "/heute - Heutiges Thema\n"
        "/test - Test-Erinnerung senden\n"
        "📋 Menü - Interaktive Bearbeitung",
        reply_markup=get_main_keyboard(),
    )


async def plan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    settings = repo.load(chat_id)
    if not settings.week_plan:
        await update.message.reply_text("Noch kein Plan hinterlegt.")
        return
    lines = ["Aktueller Wochenplan:"]
    for wd in WEEKDAYS:
        if wd in settings.week_plan:
            dp = settings.week_plan[wd]
            lines.append(f"{wd.capitalize()}: {dp.subject} ({dp.minutes} Minuten)")
    await update.message.reply_text("\n".join(lines))


async def zeiten_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    # Use shared reminder times if this is a student or parent chat
    if chat_id in get_shared_chat_ids():
        reminder_times = get_shared_reminder_times()
    else:
        settings = repo.load(chat_id)
        reminder_times = settings.reminder_times

    if not reminder_times:
        await update.message.reply_text(
            "Keine Erinnerungszeiten gesetzt. (Max 3) Format: /addzeit HH:MM"
        )
    else:
        msg = (
            "Aktuelle Zeiten: "
            + ", ".join(reminder_times)
            + " | Hinzufügen: /addzeit HH:MM | Löschen: /delzeit HH:MM"
        )
        await update.message.reply_text(msg)


async def addzeit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    if len(context.args) != 1:
        await update.message.reply_text("Bitte genau eine Zeit angeben: /addzeit HH:MM")
        return
    new_time = context.args[0]

    # Use shared reminder times if this is a student or parent chat
    if chat_id in get_shared_chat_ids():
        current_times = get_shared_reminder_times()
    else:
        settings = repo.load(chat_id)
        current_times = settings.reminder_times

    if new_time in current_times:
        await update.message.reply_text("Zeit existiert bereits und wird ignoriert.")
        return
    if len(current_times) >= MAX_REMINDERS:
        await update.message.reply_text("Maximale Anzahl (3) erreicht.")
        return
    # Validate format HH:MM
    try:
        hh, mm = new_time.split(":")
        hhi, mmi = int(hh), int(mm)
        if not (0 <= hhi < 24 and 0 <= mmi < 60):
            raise ValueError("Time out of range")
    except (ValueError, AttributeError):
        await update.message.reply_text("Ungültiges Format. Nutze HH:MM (24h).")
        return

    # Add the new time
    new_times = current_times + [new_time]
    new_times.sort()

    # Save to appropriate settings
    if chat_id in get_shared_chat_ids():
        sync_reminder_times(new_times)
    else:
        settings = repo.load(chat_id)
        settings.reminder_times = new_times
        repo.save(settings)

    await update.message.reply_text("Zeit hinzugefügt.")


async def delzeit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    if len(context.args) != 1:
        await update.message.reply_text("Bitte eine Zeit angeben: /delzeit HH:MM")
        return
    t = context.args[0]

    # Use shared reminder times if this is a student or parent chat
    if chat_id in get_shared_chat_ids():
        current_times = get_shared_reminder_times()
    else:
        settings = repo.load(chat_id)
        current_times = settings.reminder_times

    if t in current_times:
        new_times = [time for time in current_times if time != t]

        # Save to appropriate settings
        if chat_id in get_shared_chat_ids():
            sync_reminder_times(new_times)
        else:
            settings = repo.load(chat_id)
            settings.reminder_times = new_times
            repo.save(settings)

        await update.message.reply_text("Zeit gelöscht.")
    else:
        await update.message.reply_text("Zeit nicht gefunden.")


async def heute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    settings = repo.load(chat_id)
    today = WEEKDAYS[datetime.now(TIMEZONE).weekday()]
    dp = settings.week_plan.get(today)
    if not dp:
        await update.message.reply_text("Kein Eintrag für heute.")
        return
    await update.message.reply_text(
        f"Heute ({today.capitalize()}): {dp.subject} für {dp.minutes} Minuten lernen!"
    )


# ================= Inline Menü Funktionen =================

DURATION_CHOICES = [15, 20, 25, 30, 35, 40, 45, 60]


def build_main_menu() -> InlineKeyboardMarkup:
    """Build the main inline menu."""
    kb = [
        [InlineKeyboardButton("⏰ Zeiten verwalten", callback_data="menu_times")],
        [InlineKeyboardButton("📅 Wochenplan bearbeiten", callback_data="menu_plan")],
        [InlineKeyboardButton("📊 Wochenübersicht", callback_data="menu_overview")],
        [InlineKeyboardButton("🔄 Schließen", callback_data="menu_close")],
    ]
    return InlineKeyboardMarkup(kb)


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text("Hauptmenü:", reply_markup=build_main_menu())


def build_times_menu(chat_id: int) -> InlineKeyboardMarkup:
    """Build the times management menu."""
    rows = []
    # Use shared reminder times if this is a student or parent chat
    if chat_id in get_shared_chat_ids():
        reminder_times = get_shared_reminder_times()
    else:
        settings = repo.load(chat_id)
        reminder_times = settings.reminder_times

    if reminder_times:
        for t in reminder_times:
            rows.append(
                [InlineKeyboardButton(f"🗑️ {t}", callback_data=f"time_del_{t.replace(':','')}")]
            )
    if len(reminder_times) < MAX_REMINDERS:
        rows.append([InlineKeyboardButton("➕ Zeit hinzufügen", callback_data="time_add_menu")])
    rows.append([InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main")])
    return InlineKeyboardMarkup(rows)


def build_time_picker_menu() -> InlineKeyboardMarkup:
    """Build a graphical time picker menu."""
    rows = []
    # Common hours for reminders
    hours = ["06", "07", "08", "09", "12", "13", "14", "15", "16", "17", "18", "19", "20"]

    # Add title
    rows.append([InlineKeyboardButton("🕐 Stunde wählen:", callback_data="time_picker_info")])

    # Add hours in rows of 4
    hour_row = []
    for hour in hours:
        hour_row.append(InlineKeyboardButton(f"{hour}:xx", callback_data=f"time_hour_{hour}"))
        if len(hour_row) == 4:
            rows.append(hour_row)
            hour_row = []
    if hour_row:
        rows.append(hour_row)

    rows.append([InlineKeyboardButton("✏️ Eigene Zeit eingeben", callback_data="time_add")])
    rows.append([InlineKeyboardButton("⬅️ Zurück", callback_data="menu_times")])
    return InlineKeyboardMarkup(rows)


def build_minute_picker_menu(hour: str) -> InlineKeyboardMarkup:
    """Build minute picker for selected hour."""
    rows = []
    rows.append(
        [InlineKeyboardButton(f"🕐 {hour}:xx - Minute wählen:", callback_data="minute_picker_info")]
    )

    minutes = ["00", "15", "30", "45"]
    minute_row = []
    for minute in minutes:
        minute_row.append(
            InlineKeyboardButton(f"{hour}:{minute}", callback_data=f"time_select_{hour}{minute}")
        )
    rows.append(minute_row)

    rows.append(
        [InlineKeyboardButton("✏️ Andere Minute", callback_data=f"time_custom_minute_{hour}")]
    )
    rows.append([InlineKeyboardButton("⬅️ Stunden", callback_data="time_add_menu")])
    return InlineKeyboardMarkup(rows)


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

    # Professional header with spacing
    overview_lines = ["📊 **WOCHENÜBERSICHT**\n"]

    # Create a responsive table that works well on mobile
    # Use a cleaner approach with consistent spacing
    overview_lines.append("```")
    overview_lines.append("┌─────────────┬─────────────┬────────┐")
    overview_lines.append("│     Tag     │    Fach     │  Zeit  │")
    overview_lines.append("├─────────────┼─────────────┼────────┤")

    # Day emojis for better visual representation
    day_emojis = {
        "montag": "🔵",
        "dienstag": "🟢",
        "mittwoch": "🟡",
        "donnerstag": "🟠",
        "freitag": "🟣",
        "samstag": "🟤",
        "sonntag": "⚪",
    }

    for weekday in WEEKDAYS:
        day_name = weekday.capitalize()
        emoji = day_emojis.get(weekday, "📅")

        if weekday in week_plan:
            plan = week_plan[weekday]
            # Truncate subject if too long for table
            subject = plan.subject[:9] + "..." if len(plan.subject) > 12 else plan.subject
            time_str = f"{plan.minutes}min"

            # Format with exact spacing for mobile readability
            formatted_line = f"│ {emoji} {day_name:<8} │ {subject:<11} │ {time_str:>6} │"
            overview_lines.append(formatted_line)
        else:
            # Format unset days consistently
            formatted_line = f"│ {emoji} {day_name:<8} │ {'---':<11} │ {'---':>6} │"
            overview_lines.append(formatted_line)

    # Close the table
    overview_lines.append("└─────────────┴─────────────┴────────┘")
    overview_lines.append("```")

    # Add summary statistics with better formatting
    total_minutes = sum(plan.minutes for plan in week_plan.values())
    set_days = len(week_plan)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    overview_lines.append("\n📈 **ZUSAMMENFASSUNG**")
    overview_lines.append(f"📅 Geplante Tage: **{set_days}/7**")

    if total_minutes > 0:
        if hours > 0:
            overview_lines.append(f"⏱️ Gesamtzeit: **{hours}h {minutes}min**")
        else:
            overview_lines.append(f"⏱️ Gesamtzeit: **{total_minutes} Minuten**")

        avg_minutes = total_minutes // set_days if set_days > 0 else 0
        overview_lines.append(f"📊 Ø pro Tag: **{avg_minutes} Minuten**")
    else:
        overview_lines.append("⏱️ Gesamtzeit: **0 Minuten**")

    # Add reminder times with improved formatting and time-of-day icons
    overview_lines.append("\n⏰ **ERINNERUNGSZEITEN**")
    if reminder_times:
        time_display = []
        for time in reminder_times:
            hour = int(time.split(":")[0])
            if hour < 10:
                icon = "🌅"  # Early morning
            elif hour < 12:
                icon = "☀️"  # Morning
            elif hour < 17:
                icon = "🌤️"  # Afternoon
            elif hour < 20:
                icon = "🌆"  # Evening
            else:
                icon = "🌙"  # Night
            time_display.append(f"{icon} **{time}**")
        overview_lines.append(" • ".join(time_display))
    else:
        overview_lines.append("⚠️ _Keine Erinnerungszeiten festgelegt_")

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
    quick_actions = [
        InlineKeyboardButton("📅 Wochenplan", callback_data="menu_plan"),
        InlineKeyboardButton("⏰ Zeiten", callback_data="menu_times"),
    ]
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

    if data == "menu_main":
        await query.edit_message_text("Hauptmenü:", reply_markup=build_main_menu())
        await query.answer()
        return
    if data == "menu_times":
        await query.edit_message_text("Erinnerungszeiten:", reply_markup=build_times_menu(chat_id))
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
    if data.startswith("time_del_"):
        t_raw = data.removeprefix("time_del_")
        t_fmt = f"{t_raw[:2]}:{t_raw[2:]}"

        # Use shared reminder times if this is a student or parent chat
        if chat_id in get_shared_chat_ids():
            current_times = get_shared_reminder_times()
            if t_fmt in current_times:
                new_times = [time for time in current_times if time != t_fmt]
                sync_reminder_times(new_times)
                schedule_all_reminders(context.application)
        else:
            if t_fmt in settings.reminder_times:
                settings.reminder_times.remove(t_fmt)
                repo.save(settings)
                schedule_all_reminders(context.application)

        await query.edit_message_text("Erinnerungszeiten:", reply_markup=build_times_menu(chat_id))
        await query.answer("Gelöscht")
        return
    if data == "time_add":
        context.user_data["awaiting_time"] = True
        await query.answer()
        await query.edit_message_text("⏰ Bitte neue Zeit eingeben (HH:MM):")
        return
    if data == "time_add_menu":
        await query.edit_message_text("⏰ Zeit auswählen:", reply_markup=build_time_picker_menu())
        await query.answer()
        return
    if data.startswith("time_hour_"):
        hour = data.removeprefix("time_hour_")
        await query.edit_message_text(
            f"🕐 {hour}:xx - Minute wählen:", reply_markup=build_minute_picker_menu(hour)
        )
        await query.answer()
        return
    if data.startswith("time_select_"):
        time_str = data.removeprefix("time_select_")
        formatted_time = f"{time_str[:2]}:{time_str[2:]}"

        # Use shared reminder times if this is a student or parent chat
        if chat_id in get_shared_chat_ids():
            current_times = get_shared_reminder_times()
        else:
            current_times = settings.reminder_times

        if formatted_time in current_times:
            await query.answer("🕐 Diese Zeit gibt es schon!")
            return
        if len(current_times) >= MAX_REMINDERS:
            await query.answer("⏰ Maximum erreicht!")
            return

        new_times = current_times + [formatted_time]
        new_times.sort()

        # Save to appropriate settings
        if chat_id in get_shared_chat_ids():
            sync_reminder_times(new_times)
        else:
            settings.reminder_times = new_times
            repo.save(settings)

        schedule_all_reminders(context.application)
        await query.edit_message_text(
            "⏰ Zeit hinzugefügt!", reply_markup=build_times_menu(chat_id)
        )
        await query.answer("Gespeichert!")
        return
    if data.startswith("time_custom_minute_"):
        hour = data.removeprefix("time_custom_minute_")
        context.user_data["awaiting_custom_minute"] = hour
        await query.edit_message_text(f"⏰ Minute für {hour}:xx eingeben (00-59):")
        await query.answer()
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

    # Zeit Eingabe
    if context.user_data.get("awaiting_time"):
        context.user_data.pop("awaiting_time", None)
        # validate time
        try:
            hh, mm = text.split(":")
            hhi, mmi = int(hh), int(mm)
            if not (0 <= hhi < 24 and 0 <= mmi < 60):
                raise ValueError("Time out of range")
        except (ValueError, AttributeError):
            await update.message.reply_text(choice(FUNNY_TIME_ERRORS))
            return

        # Use shared reminder times if this is a student or parent chat
        if chat_id in get_shared_chat_ids():
            current_times = get_shared_reminder_times()
        else:
            current_times = settings.reminder_times

        if text in current_times:
            await update.message.reply_text(
                "🕐 Diese Zeit gibt es schon! Versuch eine andere Zeit."
            )
            return
        if len(current_times) >= MAX_REMINDERS:
            await update.message.reply_text(
                "⏰ Du hast schon das Maximum erreicht! Lösche erst eine Zeit."
            )
            return

        new_times = current_times + [text]
        new_times.sort()

        # Save to appropriate settings
        if chat_id in get_shared_chat_ids():
            sync_reminder_times(new_times)
        else:
            settings.reminder_times = new_times
            repo.save(settings)

        schedule_all_reminders(context.application)
        await update.message.reply_text("⏰ Zeit gespeichert!", reply_markup=get_main_keyboard())
        return

    # Custom minute input
    if "awaiting_custom_minute" in context.user_data:
        hour = context.user_data.pop("awaiting_custom_minute")
        try:
            minute = int(text)
            if not (0 <= minute <= 59):
                raise ValueError("Minute out of range")
            formatted_time = f"{hour}:{minute:02d}"
        except (ValueError, AttributeError):
            await update.message.reply_text(choice(FUNNY_TIME_ERRORS))
            return

        # Use shared reminder times if this is a student or parent chat
        if chat_id in get_shared_chat_ids():
            current_times = get_shared_reminder_times()
        else:
            current_times = settings.reminder_times

        if formatted_time in current_times:
            await update.message.reply_text("🕐 Diese Zeit gibt es schon! Versuch eine andere.")
            return
        if len(current_times) >= MAX_REMINDERS:
            await update.message.reply_text("⏰ Du hast schon das Maximum erreicht!")
            return

        new_times = current_times + [formatted_time]
        new_times.sort()

        # Save to appropriate settings
        if chat_id in get_shared_chat_ids():
            sync_reminder_times(new_times)
        else:
            settings.reminder_times = new_times
            repo.save(settings)

        schedule_all_reminders(context.application)
        await update.message.reply_text("⏰ Zeit gespeichert!", reply_markup=get_main_keyboard())
        return
    # Minuten Eingabe
    if "awaiting_minutes" in context.user_data:
        weekday, subject = context.user_data.pop("awaiting_minutes")
        try:
            m = int(text)
            if not (MIN_MINUTES <= m <= MAX_MINUTES):
                raise ValueError("Minutes out of range")
        except (ValueError, AttributeError):
            await update.message.reply_text(choice(FUNNY_NUMBER_ERRORS))
            return

        # Use shared plan if this is a parent or student chat
        if chat_id in get_shared_chat_ids():
            week_plan = get_shared_week_plan()
            week_plan[weekday] = DayPlan(subject=subject, minutes=m)
            sync_week_plan(week_plan)
        else:
            settings.week_plan[weekday] = DayPlan(subject=subject, minutes=m)
            repo.save(settings)

        schedule_all_reminders(context.application)
        await update.message.reply_text(
            f"Gespeichert: {weekday.capitalize()} – {subject} ({m} Minuten).",
            reply_markup=get_main_keyboard(),
        )
        return
    # Unbenutzter freier Text
    await update.message.reply_text(choice(FUNNY_ERROR_MESSAGES))


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


async def daily_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.info("daily_check: Starting 20:00 daily check")

    if not STUDENT_CHAT_ID:
        LOGGER.warning("daily_check: STUDENT_CHAT_ID not set - skipping daily check")
        return

    LOGGER.info(f"daily_check: Sending question to student chat {STUDENT_CHAT_ID}")

    try:
        settings = repo.load(STUDENT_CHAT_ID)
        today = WEEKDAYS[datetime.now(TIMEZONE).weekday()]
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
        else:
            LOGGER.info(
                "daily_check: No parent notification (PARENT_CHAT_ID not set or same as student)"
            )

    except Exception as e:
        LOGGER.error(f"daily_check: Error during daily check: {e}", exc_info=True)


async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data or {}
    chat_id = job_data.get("chat_id")
    if not chat_id:
        return
    settings = repo.load(chat_id)
    msg = build_reminder_message(settings)
    await context.bot.send_message(chat_id=chat_id, text=msg)
    # Info an Elternteil/Betreuer
    if PARENT_CHAT_ID and PARENT_CHAT_ID != chat_id:
        await context.bot.send_message(
            chat_id=PARENT_CHAT_ID, text=f"(Info) Erinnerung an Schüler-Chat {chat_id} gesendet."
        )


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

    # Per-user reminders
    reminder_count = 0
    for uid in repo.list_user_ids():
        settings = repo.load(uid)
        for rt in settings.reminder_times:
            try:
                hh, mm = map(int, rt.split(":"))
            except (ValueError, AttributeError) as e:
                LOGGER.warning(
                    f"schedule_all_reminders: Invalid time format '{rt}' for user {uid}: {e}"
                )
                continue
            app.job_queue.run_daily(
                reminder_job,
                time=time(hour=hh, minute=mm, tzinfo=TIMEZONE),
                name=f"reminder_{uid}_{rt}",
                data={"chat_id": uid},
            )
            reminder_count += 1
            LOGGER.debug(f"schedule_all_reminders: Scheduled reminder for user {uid} at {rt}")

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
        f"schedule_all_reminders: Completed. Scheduled {reminder_count} user reminders + 1 daily check"
    )


def build_app():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN nicht gesetzt")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("plan", plan_cmd))
    app.add_handler(CommandHandler("zeiten", zeiten_cmd))
    app.add_handler(CommandHandler("addzeit", addzeit_cmd))
    app.add_handler(CommandHandler("delzeit", delzeit_cmd))
    app.add_handler(CommandHandler("heute", heute_cmd))
    app.add_handler(CommandHandler("test", test_cmd))
    app.add_handler(CommandHandler("testdaily", test_daily_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    # Callback Handler Reihenfolge: zuerst eigene Menüs, dann learned callbacks
    app.add_handler(CallbackQueryHandler(on_learned_response, pattern="^learned_"))
    app.add_handler(CallbackQueryHandler(handle_callback))
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
