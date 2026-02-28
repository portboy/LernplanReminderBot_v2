"""Main bot application — refactored architecture (v2)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.config import BotConfig, load_config
from core.logging_config import setup_logging
from models.settings import SettingsRepository, WEEKDAYS
from services import LernplanService
from ui.keyboards import KeyboardBuilder
from ui.messages import MessageBuilder

LOGGER = logging.getLogger(__name__)


# ============================================================================
# Application context — replaces flat module-level globals
# ============================================================================


@dataclass
class BotContext:
    """Bundles all shared instances. Stored in ``application.bot_data["ctx"]``."""

    config: BotConfig
    repo: SettingsRepository
    service: LernplanService
    keyboards: KeyboardBuilder
    messages: MessageBuilder
    timezone: ZoneInfo


def get_ctx(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    """Retrieve the shared ``BotContext`` from a handler's *context*."""
    return context.bot_data["ctx"]


# ============================================================================
# Command Handlers
# ============================================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    ctx = get_ctx(context)
    chat_id = update.effective_chat.id
    user = update.effective_user
    LOGGER.info(f"🆕 /start from chat_id={chat_id}, user={user.first_name}")

    ctx.repo.load(chat_id)  # ensure settings file exists
    await update.message.reply_text(
        f"Willkommen beim Lernplan Reminder Bot! 👋\n\n"
        f"Deine Chat-ID: `{chat_id}`\n"
        f"Nutze den Menü-Button oder /menu.",
        reply_markup=ctx.keyboards.get_main_keyboard(),
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    ctx = get_ctx(context)
    await update.message.reply_text(
        "Nutze /menu für das Hauptmenü, /plan für den Wochenplan und /heute für die Übersicht.",
        reply_markup=ctx.keyboards.get_main_keyboard(),
    )


async def plan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    ctx = get_ctx(context)
    await update.message.reply_text(
        "Wochentage wählen:", reply_markup=ctx.keyboards.build_weekday_menu()
    )


async def heute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    ctx = get_ctx(context)
    chat_id = update.effective_chat.id
    summary = ctx.service.get_weekly_summary(chat_id)
    text = ctx.messages.build_weekly_overview(summary["week_plan"], summary["reminder_times"])
    await update.message.reply_text(text, parse_mode="Markdown")


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    ctx = get_ctx(context)
    await update.message.reply_text(
        "Hauptmenü:", reply_markup=ctx.keyboards.build_main_menu()
    )


async def test_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    ctx = get_ctx(context)
    chat_id = update.effective_chat.id
    settings = ctx.repo.load(chat_id)
    await update.message.reply_text(ctx.messages.build_reminder_message(settings))


async def test_daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text("🧪 Testing daily check function...")
    try:
        await daily_check(context)
        await update.message.reply_text("✅ Daily check function executed successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Daily check failed: {e}")
        LOGGER.error(f"test_daily_cmd: {e}", exc_info=True)


# ============================================================================
# Callback Query Handler
# ============================================================================


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: C901
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    chat_id = query.message.chat_id
    ctx = get_ctx(context)

    try:
        # --- skip comment -----------------------------------------------
        if data == "skip_comment":
            if "awaiting_comment" in context.user_data:
                context.user_data.pop("awaiting_comment")
                await query.edit_message_text("Okay, kein Kommentar. Bis morgen! 🐴")
                await query.answer()
                return

        # --- noop (informational buttons) --------------------------------
        if data == "noop":
            await query.answer()
            return

        # --- main menu ---------------------------------------------------
        if data == "menu_main":
            await query.edit_message_text(
                "Hauptmenü:", reply_markup=ctx.keyboards.build_main_menu()
            )
            await query.answer()
            return

        if data in ("menu_plan", "plan_days"):
            await query.edit_message_text(
                "Wochentage wählen:", reply_markup=ctx.keyboards.build_weekday_menu()
            )
            await query.answer()
            return

        if data == "menu_overview":
            summary = ctx.service.get_weekly_summary(chat_id)
            text = ctx.messages.build_weekly_overview(
                summary["week_plan"], summary["reminder_times"]
            )
            try:
                await query.edit_message_text(
                    text,
                    reply_markup=ctx.keyboards.build_overview_menu(summary["week_plan"]),
                    parse_mode="Markdown",
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    raise
            await query.answer()
            return

        if data == "menu_today":
            settings = ctx.repo.load(chat_id)
            text = ctx.messages.build_today_overview(settings)
            try:
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main")]
                    ]),
                    parse_mode="Markdown",
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    raise
            await query.answer()
            return

        if data == "menu_weekly_stats":
            stats = ctx.service.get_weekly_statistics(chat_id, days=7)
            text = ctx.messages.build_weekly_statistics(stats)
            try:
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Zurück", callback_data="menu_main")]
                    ]),
                    parse_mode="Markdown",
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    raise
            await query.answer()
            return

        if data == "menu_close":
            await query.edit_message_text("Menü geschlossen.")
            await query.message.reply_text(
                "Nutze den Menü-Button unten oder /menu.",
                reply_markup=ctx.keyboards.get_main_keyboard(),
            )
            await query.answer()
            return

        # --- reminder time management ------------------------------------
        if data == "menu_times":
            cfg = ctx.config
            if chat_id in ctx.service.get_shared_chat_ids(cfg.student_chat_id, cfg.parent_chat_id):
                times = ctx.service.get_shared_reminder_times(cfg.student_chat_id, cfg.parent_chat_id)
            else:
                times = list(ctx.repo.load(chat_id).reminder_times)

            await query.edit_message_text(
                "⏰ **Erinnerungszeiten**\n\nHier verwaltest du deine täglichen Erinnerungen.",
                reply_markup=ctx.keyboards.build_times_menu(times),
                parse_mode="Markdown",
            )
            await query.answer()
            return

        if data == "add_time":
            await query.edit_message_text(
                "Stunde wählen:", reply_markup=ctx.keyboards.build_hour_picker()
            )
            await query.answer()
            return

        if data.startswith("pick_hour_"):
            hour = data.removeprefix("pick_hour_")
            await query.edit_message_text(
                f"Minute wählen (Stunde {hour}):",
                reply_markup=ctx.keyboards.build_minute_picker(hour),
            )
            await query.answer()
            return

        if data.startswith("pick_minute_"):
            parts = data.removeprefix("pick_minute_").split("_", 1)
            hour, minute = parts[0], parts[1]
            time_str = f"{hour}:{minute}"
            cfg = ctx.config
            ok, msg = ctx.service.add_reminder_time(
                chat_id, time_str, cfg.max_reminder_times,
                cfg.student_chat_id, cfg.parent_chat_id,
            )
            if ok:
                schedule_all_reminders(context.application)
            await query.answer(msg, show_alert=not ok)

            # Refresh times menu
            if chat_id in ctx.service.get_shared_chat_ids(cfg.student_chat_id, cfg.parent_chat_id):
                times = ctx.service.get_shared_reminder_times(cfg.student_chat_id, cfg.parent_chat_id)
            else:
                times = list(ctx.repo.load(chat_id).reminder_times)
            await query.edit_message_text(
                "⏰ **Erinnerungszeiten**\n\nHier verwaltest du deine täglichen Erinnerungen.",
                reply_markup=ctx.keyboards.build_times_menu(times),
                parse_mode="Markdown",
            )
            return

        if data.startswith("del_time_"):
            time_str = data.removeprefix("del_time_")
            cfg = ctx.config
            ok, msg = ctx.service.remove_reminder_time(
                chat_id, time_str, cfg.student_chat_id, cfg.parent_chat_id,
            )
            if ok:
                schedule_all_reminders(context.application)
            await query.answer(msg, show_alert=not ok)

            if chat_id in ctx.service.get_shared_chat_ids(cfg.student_chat_id, cfg.parent_chat_id):
                times = ctx.service.get_shared_reminder_times(cfg.student_chat_id, cfg.parent_chat_id)
            else:
                times = list(ctx.repo.load(chat_id).reminder_times)
            await query.edit_message_text(
                "⏰ **Erinnerungszeiten**\n\nHier verwaltest du deine täglichen Erinnerungen.",
                reply_markup=ctx.keyboards.build_times_menu(times),
                parse_mode="Markdown",
            )
            return

        # --- morning planning --------------------------------------------
        if data == "morning_subjects":
            jokers = ctx.service.get_jokers_available(chat_id)
            await query.edit_message_text(
                "Guten Morgen! ☀️ Plan für heute?",
                reply_markup=ctx.keyboards.build_morning_planning_keyboard(jokers),
            )
            await query.answer()
            return

        if data.startswith("plan_subject_") and data.count("_") == 2:
            subject = data.split("_", 2)[2]
            context.user_data["dynamic_subject"] = subject
            await query.edit_message_text(
                f"Welche Zeit passt für {subject}?",
                reply_markup=ctx.keyboards.build_dynamic_time_menu(subject),
            )
            await query.answer()
            return

        if data.startswith("plan_time_"):
            time_str = data.removeprefix("plan_time_")
            subject = context.user_data.get("dynamic_subject")
            if not subject:
                await query.answer("Bitte zuerst ein Fach wählen.", show_alert=True)
                return
            if not ctx.service.add_dynamic_plan_entry(chat_id, subject, time_str):
                await query.answer("Diese Zeit ist bereits vorbei.", show_alert=True)
                return
            if context.application:
                schedule_dynamic_job(context.application, chat_id, subject, time_str, ctx)
            await query.edit_message_text(
                f"Geplant: {subject} um {time_str}. Ich erinnere dich rechtzeitig!"
            )
            await query.answer("Plan gespeichert!")
            context.user_data.pop("dynamic_subject", None)
            return

        if data == "use_joker":
            if ctx.service.use_joker(chat_id):
                await query.edit_message_text("Genieß den Tag! ☀️ Joker eingesetzt.")
                await query.answer("Joker genutzt!")
            else:
                await query.answer("Keine Joker verfügbar.", show_alert=True)
            return

        # --- week planning -----------------------------------------------
        if data.startswith("plan_day_"):
            weekday = data.removeprefix("plan_day_")
            context.user_data["plan_weekday"] = weekday
            await query.edit_message_text(
                f"Fach für {weekday.capitalize()} wählen:",
                reply_markup=ctx.keyboards.build_subject_menu(weekday),
            )
            await query.answer()
            return

        if data.startswith("plan_subject_") and data.count("_") == 3:
            parts = data.split("_", 3)
            weekday, subject = parts[2], parts[3]
            context.user_data["plan_subject"] = subject
            context.user_data["plan_weekday"] = weekday
            await query.edit_message_text(
                f"Minuten für {weekday.capitalize()} – {subject} wählen:",
                reply_markup=ctx.keyboards.build_minutes_menu(weekday, subject),
            )
            await query.answer()
            return

        if data.startswith("plan_minutes_custom_"):
            parts = data.split("_", 4)
            weekday, subject = parts[3], parts[4]
            context.user_data["awaiting_minutes"] = (weekday, subject)
            await query.edit_message_text(
                f"Eigene Minutenanzahl für {weekday.capitalize()} – {subject} eingeben "
                f"(Zahl {ctx.config.min_minutes}-{ctx.config.max_minutes}):"
            )
            await query.answer()
            return

        if data.startswith("plan_minutes_") and not data.startswith("plan_minutes_custom_"):
            parts = data.split("_", 4)
            weekday, subject, minutes = parts[2], parts[3], int(parts[4])
            cfg = ctx.config
            ctx.service.update_day_plan(
                chat_id, weekday, subject, minutes, cfg.student_chat_id, cfg.parent_chat_id
            )
            schedule_all_reminders(context.application)
            await query.edit_message_text(
                f"Gespeichert: {weekday.capitalize()} – {subject} ({minutes} Minuten)",
                reply_markup=ctx.keyboards.build_weekday_menu(),
            )
            await query.answer("Gespeichert")
            return

    except Exception as e:
        LOGGER.error(f"Error handling callback {data}: {e}", exc_info=True)
        await query.answer("Ein Fehler ist aufgetreten.", show_alert=True)

    await query.answer()


# ============================================================================
# Learned-response handler (daily check)
# ============================================================================


async def on_learned_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    data = query.data
    ctx = get_ctx(context)
    chat_id = query.message.chat_id
    LOGGER.info(f"on_learned_response: '{data}' from chat {chat_id}")

    try:
        if data == "learned_yes":
            img = ctx.messages.get_random_happy_image()
            await query.edit_message_text("Super! Weiter so! 🐴🎉")
            await context.bot.send_photo(chat_id=chat_id, photo=img)
            # Archive with positive response
            ctx.service.archive_daily_to_history(chat_id, learned_response="yes")
        elif data == "learned_no":
            gif = ctx.messages.get_random_sad_gif()
            await query.edit_message_text("Vielleicht klappt es morgen besser. 🐴")
            await context.bot.send_animation(chat_id=chat_id, animation=gif)
            ctx.service.archive_daily_to_history(chat_id, learned_response="no")
        else:
            return

        # Ask for optional comment
        await context.bot.send_message(
            chat_id=chat_id,
            text="💬 Möchtest du noch einen Kommentar hinzufügen?\n\n"
                 "✍️ Schreibe einfach deine Nachricht oder\n"
                 "🎤 sende eine Sprachnachricht.\n\n"
                 "Oder klicke auf 'Überspringen'.",
            reply_markup=ctx.keyboards.build_skip_comment_keyboard(),
        )
        context.user_data["awaiting_comment"] = data.removeprefix("learned_")

        # Notify parent
        cfg = ctx.config
        if cfg.parent_chat_id and cfg.parent_chat_id != chat_id:
            label = "JA gelernt ✅" if data == "learned_yes" else "NEIN gelernt ❌"
            await context.bot.send_message(
                chat_id=cfg.parent_chat_id, text=f"Antwort Schüler: {label}"
            )

    except Exception as e:
        LOGGER.error(f"on_learned_response error: {e}", exc_info=True)


# ============================================================================
# Text and Voice Handlers
# ============================================================================


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    ctx = get_ctx(context)
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()

    if text == "/skip" and "awaiting_comment" in context.user_data:
        context.user_data.pop("awaiting_comment")
        await update.message.reply_text(
            "Okay, kein Kommentar. Bis morgen! 🐴",
            reply_markup=ctx.keyboards.get_main_keyboard(),
        )
        return

    if "awaiting_comment" in context.user_data:
        context.user_data.pop("awaiting_comment")
        cfg = ctx.config
        if cfg.parent_chat_id and cfg.parent_chat_id != chat_id:
            await context.bot.send_message(
                chat_id=cfg.parent_chat_id, text=f"💬 Kommentar vom Schüler:\n{text}"
            )
        await update.message.reply_text(
            "Danke für deinen Kommentar! Bis morgen! 🐴",
            reply_markup=ctx.keyboards.get_main_keyboard(),
        )
        return

    if text == "📋 Menü":
        await update.message.reply_text(
            "Hauptmenü:", reply_markup=ctx.keyboards.build_main_menu()
        )
        return

    if "awaiting_minutes" in context.user_data:
        weekday, subject = context.user_data.pop("awaiting_minutes")
        try:
            minutes_value = int(text)
            if not (ctx.config.min_minutes <= minutes_value <= ctx.config.max_minutes):
                raise ValueError
        except (ValueError, AttributeError):
            await update.message.reply_text(ctx.messages.get_funny_number_error())
            return

        cfg = ctx.config
        ctx.service.update_day_plan(
            chat_id, weekday, subject, minutes_value,
            cfg.student_chat_id, cfg.parent_chat_id,
        )
        schedule_all_reminders(context.application)
        await update.message.reply_text(
            f"Gespeichert: {weekday.capitalize()} – {subject} ({minutes_value} Minuten).",
            reply_markup=ctx.keyboards.get_main_keyboard(),
        )
        return

    await update.message.reply_text(ctx.messages.get_funny_error())


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.voice:
        return

    ctx = get_ctx(context)
    cfg = ctx.config
    chat_id = message.chat_id

    if chat_id != cfg.student_chat_id:
        return

    # Voice comment after daily check
    if "awaiting_comment" in context.user_data:
        context.user_data.pop("awaiting_comment")
        if cfg.parent_chat_id and cfg.parent_chat_id != chat_id:
            try:
                await context.bot.send_message(
                    chat_id=cfg.parent_chat_id, text="🎤 Sprachkommentar vom Schüler:"
                )
                await context.bot.send_voice(
                    chat_id=cfg.parent_chat_id, voice=message.voice.file_id,
                )
            except Exception as e:
                LOGGER.error(f"Failed to forward voice comment: {e}")
        await message.reply_text(
            "Danke für deinen Kommentar! Bis morgen! 🐴",
            reply_markup=ctx.keyboards.get_main_keyboard(),
        )
        return

    # Mark most recent incomplete dynamic entry as complete
    settings = ctx.repo.load(chat_id)
    now = datetime.now(ctx.timezone)
    today_iso = now.date().isoformat()
    now_time = now.time()

    past_candidate = None
    past_time = None
    for entry in settings.daily_dynamic_plan:
        if entry.get("date_iso") != today_iso or entry.get("completed"):
            continue
        try:
            hh, mm = map(int, (entry.get("time_str") or "").split(":"))
            et = time(hour=hh, minute=mm)
        except (ValueError, TypeError):
            continue
        if et <= now_time and (past_time is None or et < past_time):
            past_candidate = entry
            past_time = et

    if past_candidate:
        past_candidate["completed"] = True
        ctx.repo.save(settings)

    forwarded = False
    if cfg.parent_chat_id:
        try:
            await context.bot.send_voice(
                chat_id=cfg.parent_chat_id,
                voice=message.voice.file_id,
                caption="🎙️ Sprachnachricht vom Schüler",
            )
            forwarded = True
        except Exception as exc:
            LOGGER.error(f"Failed to forward voice: {exc}")

    await message.reply_text(
        "✅ Nachricht weitergeleitet und Plan aktualisiert." if forwarded
        else "✅ Plan aktualisiert."
    )


# ============================================================================
# Scheduled Jobs
# ============================================================================


async def morning_planning_prompt(context: ContextTypes.DEFAULT_TYPE) -> None:
    ctx = get_ctx(context)
    cfg = ctx.config
    if not cfg.student_chat_id:
        return
    try:
        jokers = ctx.service.get_jokers_available(cfg.student_chat_id)
        await context.bot.send_message(
            chat_id=cfg.student_chat_id,
            text="Guten Morgen! ☀️ Plan für heute?",
            reply_markup=ctx.keyboards.build_morning_planning_keyboard(jokers),
        )
    except Exception as e:
        LOGGER.error(f"morning_planning_prompt: {e}", exc_info=True)


async def daily_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily check and archive learning data."""
    ctx = get_ctx(context)
    cfg = ctx.config
    if not cfg.student_chat_id:
        return

    try:
        settings = ctx.repo.load(cfg.student_chat_id)
        now_dt = datetime.now(ctx.timezone)
        today = WEEKDAYS[now_dt.weekday()]
        today_iso = now_dt.date().isoformat()

        todays_entries = [
            e for e in settings.daily_dynamic_plan if e.get("date_iso") == today_iso
        ]

        def sort_key(e: dict) -> int:
            try:
                hh, mm = map(int, e.get("time_str", "").split(":"))
                return hh * 60 + mm
            except (ValueError, TypeError):
                return 24 * 60 + 1

        todays_sorted = sorted(todays_entries, key=sort_key)
        completed_count = sum(1 for e in todays_sorted if e.get("completed"))

        report = ctx.messages.build_daily_report(
            todays_sorted, completed_count, now_dt.strftime("%d.%m.%Y")
        )

        day_plan = settings.week_plan.get(today)
        text = (
            "Hast du heute auch gelernt?"
            if day_plan
            else "Heute war kein Lernplan-Eintrag hinterlegt – hast du trotzdem gelernt?"
        )

        await context.bot.send_message(
            chat_id=cfg.student_chat_id,
            text=text,
            reply_markup=ctx.keyboards.build_learned_response_keyboard(),
        )

        if cfg.parent_chat_id and cfg.parent_chat_id != cfg.student_chat_id:
            await context.bot.send_message(
                chat_id=cfg.parent_chat_id,
                text="(Info) 20-Uhr-Abfrage an Schüler gesendet.",
            )
            await context.bot.send_message(chat_id=cfg.parent_chat_id, text=report)

        # NOTE: archive_daily_to_history is called from on_learned_response
        # which runs AFTER the student answers. Here we only clear dynamic plan.
        settings.daily_dynamic_plan = []
        ctx.repo.save(settings)

    except Exception as e:
        LOGGER.error(f"daily_check: {e}", exc_info=True)


async def weekly_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    ctx = get_ctx(context)
    cfg = ctx.config
    if not cfg.student_chat_id:
        return
    try:
        stats = ctx.service.get_weekly_statistics(cfg.student_chat_id, days=7)
        text = ctx.messages.build_weekly_statistics(stats)
        await context.bot.send_message(
            chat_id=cfg.student_chat_id, text=text, parse_mode="Markdown"
        )
        if cfg.parent_chat_id and cfg.parent_chat_id != cfg.student_chat_id:
            await context.bot.send_message(
                chat_id=cfg.parent_chat_id,
                text=f"📊 Wochenzusammenfassung\n\n{text}",
                parse_mode="Markdown",
            )
    except Exception as e:
        LOGGER.error(f"weekly_summary: {e}", exc_info=True)


async def dynamic_plan_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data or {}
    chat_id = job_data.get("chat_id")
    subject = job_data.get("subject")
    time_str = job_data.get("time_str")
    if not all([chat_id, subject, time_str]):
        return
    try:
        await context.bot.send_message(
            chat_id=chat_id, text=f"🔔 Zeit für {subject} um {time_str}! Viel Erfolg!"
        )
    except Exception as e:
        LOGGER.error(f"dynamic_plan_job: {e}", exc_info=True)


def schedule_dynamic_job(
    app: Application, chat_id: int, subject: str, time_str: str, ctx: BotContext
) -> bool:
    try:
        hh, mm = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        return False

    now_dt = datetime.now(ctx.timezone)
    target = datetime.combine(now_dt.date(), time(hour=hh, minute=mm), tzinfo=ctx.timezone)
    if target <= now_dt:
        return False

    safe_subject = abs(hash(subject)) % 10000
    job_name = f"dynamic_{chat_id}_{hh:02d}{mm:02d}_{safe_subject}"
    for job in app.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()

    app.job_queue.run_once(
        dynamic_plan_job,
        when=target,
        name=job_name,
        data={"chat_id": chat_id, "subject": subject, "time_str": time_str},
    )
    return True


def schedule_all_reminders(app: Application) -> None:
    """Schedule / refresh all reminder jobs."""
    ctx: BotContext = app.bot_data["ctx"]
    cfg = ctx.config
    tz = ctx.timezone

    # Remove dynamic jobs
    for job in list(app.job_queue.jobs()):
        if job.name and job.name.startswith("dynamic_"):
            job.schedule_removal()

    # Re-schedule today's dynamic entries
    now = datetime.now(tz)
    today_iso = now.date().isoformat()
    for uid in ctx.repo.list_user_ids():
        settings = ctx.repo.load(uid)
        todays = [e for e in settings.daily_dynamic_plan if e.get("date_iso") == today_iso]
        if len(todays) != len(settings.daily_dynamic_plan):
            settings.daily_dynamic_plan = todays
            ctx.repo.save(settings)
        for entry in todays:
            if entry.get("completed"):
                continue
            subj = entry.get("subject")
            ts = entry.get("time_str")
            if subj and ts:
                schedule_dynamic_job(app, uid, subj, ts, ctx)

    if not cfg.student_chat_id:
        LOGGER.warning("Student chat ID not configured — skipping system jobs")
        return

    # System jobs (only schedule once)
    if not any(j.name == "morning_planning_prompt" for j in app.job_queue.jobs()):
        h, m = map(int, cfg.morning_prompt_time.split(":"))
        app.job_queue.run_daily(
            morning_planning_prompt,
            time=time(hour=h, minute=m, tzinfo=tz),
            name="morning_planning_prompt",
        )
        LOGGER.info(f"Scheduled morning prompt at {cfg.morning_prompt_time}")

    if not any(j.name == "daily_check_20" for j in app.job_queue.jobs()):
        h, m = map(int, cfg.daily_check_time.split(":"))
        app.job_queue.run_daily(
            daily_check,
            time=time(hour=h, minute=m, tzinfo=tz),
            name="daily_check_20",
        )
        LOGGER.info(f"Scheduled daily check at {cfg.daily_check_time}")

    if not any(j.name == "weekly_summary" for j in app.job_queue.jobs()):
        app.job_queue.run_daily(
            weekly_summary,
            time=time(hour=21, minute=0, tzinfo=tz),
            days=(6,),
            name="weekly_summary",
        )
        LOGGER.info("Scheduled weekly summary for Sundays 21:00")

    LOGGER.info(f"Config: STUDENT={cfg.student_chat_id}, PARENT={cfg.parent_chat_id}")


# ============================================================================
# Application Setup
# ============================================================================


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.error(f"Unhandled exception: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "🤖 Ein Fehler ist aufgetreten. Bitte versuche es erneut."
            )
        except Exception:
            pass


def build_app(ctx: BotContext) -> Application:
    if not ctx.config.telegram_token or ctx.config.telegram_token == "YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "TELEGRAM_TOKEN not set. Please configure userconfig/bot_config.json "
            "or set TELEGRAM_TOKEN environment variable."
        )

    app = ApplicationBuilder().token(ctx.config.telegram_token).build()
    app.bot_data["ctx"] = ctx

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("plan", plan_cmd))
    app.add_handler(CommandHandler("heute", heute_cmd))
    app.add_handler(CommandHandler("test", test_cmd))
    app.add_handler(CommandHandler("testdaily", test_daily_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))

    # Callback handlers (order matters)
    app.add_handler(CallbackQueryHandler(on_learned_response, pattern="^learned_"))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Message handlers
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text))

    app.add_error_handler(error_handler)
    schedule_all_reminders(app)
    return app


def main() -> None:
    cfg = load_config()
    setup_logging(cfg.log_level)

    tz = ZoneInfo(cfg.timezone)
    data_dir = Path(cfg.data_dir)
    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    repo = SettingsRepository(data_dir)
    service = LernplanService(repo, tz)
    keyboards = KeyboardBuilder(cfg)
    messages = MessageBuilder(cfg, tz)

    ctx = BotContext(
        config=cfg, repo=repo, service=service,
        keyboards=keyboards, messages=messages, timezone=tz,
    )

    LOGGER.info("=" * 60)
    LOGGER.info("Lernplan Reminder Bot v2 Starting")
    LOGGER.info("=" * 60)
    LOGGER.info(f"Student Chat ID: {cfg.student_chat_id}")
    LOGGER.info(f"Parent Chat ID: {cfg.parent_chat_id}")
    LOGGER.info(f"Timezone: {cfg.timezone}")
    LOGGER.info(f"Subjects: {', '.join(cfg.get_subject_names())}")
    LOGGER.info("=" * 60)

    if not cfg.student_chat_id:
        raise ValueError("STUDENT_CHAT_ID is required for bot operation")
    if not cfg.parent_chat_id:
        LOGGER.warning("PARENT_CHAT_ID not set — parent notifications disabled")

    app = build_app(ctx)
    LOGGER.info("Bot started. Polling for updates…")
    app.run_polling()


if __name__ == "__main__":
    main()
