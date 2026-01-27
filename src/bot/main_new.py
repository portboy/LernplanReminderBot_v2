"""Main bot application with refactored architecture."""

from __future__ import annotations

import logging
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Update
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
from models.settings import DayPlan, SettingsRepository, WEEKDAYS
from services import LernplanService
from ui.keyboards import KeyboardBuilder
from ui.messages import MessageBuilder

LOGGER = logging.getLogger(__name__)

# Global instances (initialized in main)
config: BotConfig
repo: SettingsRepository
lernplan_service: LernplanService
keyboard_builder: KeyboardBuilder
message_builder: MessageBuilder
timezone: ZoneInfo


def init_globals(cfg: BotConfig) -> None:
    """Initialize global instances."""
    global config, repo, lernplan_service, keyboard_builder, message_builder, timezone
    
    config = cfg
    timezone = ZoneInfo(config.timezone)
    
    # Setup data directory
    data_dir = Path(config.data_dir)
    if not data_dir.is_absolute():
        # If relative path, use current working directory (not package location)
        data_dir = Path.cwd() / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    
    repo = SettingsRepository(data_dir)
    lernplan_service = LernplanService(repo, timezone)
    keyboard_builder = KeyboardBuilder(config)
    message_builder = MessageBuilder(config, timezone)
    
    LOGGER.info(f"Initialized with timezone: {config.timezone}")
    LOGGER.info(f"Data directory: {data_dir}")
    LOGGER.info(f"Allowed subjects: {config.get_subject_names()}")


# ============================================================================
# Command Handlers
# ============================================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not update.message:
        return
    chat_id = update.effective_chat.id
    repo.load(chat_id)  # Initialize user settings
    await update.message.reply_text(
        "Willkommen beim Lernplan Reminder Bot! Nutze den Menü-Button oder /menu.",
        reply_markup=keyboard_builder.get_main_keyboard(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.message:
        return
    await update.message.reply_text(
        "Nutze /menu für das Hauptmenü, /plan für den Wochenplan und /heute für die Übersicht.",
        reply_markup=keyboard_builder.get_main_keyboard(),
    )


async def plan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /plan command."""
    if not update.message:
        return
    await update.message.reply_text(
        "Wochentage wählen:", reply_markup=keyboard_builder.build_weekday_menu()
    )


async def heute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /heute command."""
    if not update.message:
        return
    chat_id = update.effective_chat.id
    summary = lernplan_service.get_weekly_summary(chat_id)
    overview_text = message_builder.build_weekly_overview(
        summary["week_plan"], summary["reminder_times"]
    )
    await update.message.reply_text(overview_text, parse_mode="Markdown")


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu command."""
    if not update.message:
        return
    await update.message.reply_text(
        "Hauptmenü:", reply_markup=keyboard_builder.build_main_menu()
    )


async def test_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test command to show today's reminder."""
    if not update.message:
        return
    chat_id = update.effective_chat.id
    settings = repo.load(chat_id)
    await update.message.reply_text(message_builder.build_reminder_message(settings))


async def test_daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test command to manually trigger the daily check."""
    if not update.message:
        return
    await update.message.reply_text("🧪 Testing daily check function...")
    try:
        await daily_check(context)
        await update.message.reply_text("✅ Daily check function executed successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Daily check failed: {e}")
        LOGGER.error(f"test_daily_cmd: Error testing daily check: {e}", exc_info=True)


# ============================================================================
# Callback Query Handler
# ============================================================================


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries from inline keyboards."""
    query = update.callback_query
    if not query:
        return
    
    data = query.data or ""
    chat_id = query.message.chat_id

    try:
        # Main menu navigation
        if data == "menu_main":
            await query.edit_message_text(
                "Hauptmenü:", reply_markup=keyboard_builder.build_main_menu()
            )
            await query.answer()
            return

        if data == "menu_plan" or data == "plan_days":
            await query.edit_message_text(
                "Wochentage wählen:", reply_markup=keyboard_builder.build_weekday_menu()
            )
            await query.answer()
            return

        if data == "menu_overview":
            summary = lernplan_service.get_weekly_summary(chat_id)
            overview_text = message_builder.build_weekly_overview(
                summary["week_plan"], summary["reminder_times"]
            )
            await query.edit_message_text(
                overview_text,
                reply_markup=keyboard_builder.build_overview_menu(summary["week_plan"]),
                parse_mode="Markdown",
            )
            await query.answer()
            return

        if data == "menu_close":
            await query.edit_message_text("Menü geschlossen.")
            await query.message.reply_text(
                "Nutze den Menü-Button unten oder /menu.",
                reply_markup=keyboard_builder.get_main_keyboard(),
            )
            await query.answer()
            return

        # Morning planning
        if data == "morning_subjects":
            jokers_left = lernplan_service.get_jokers_available(chat_id)
            await query.edit_message_text(
                "Guten Morgen! ☀️ Plan für heute?",
                reply_markup=keyboard_builder.build_morning_planning_keyboard(jokers_left),
            )
            await query.answer()
            return

        if data.startswith("plan_subject_") and data.count("_") == 2:
            # Morning planning subject selection
            subject = data.split("_", 2)[2]
            context.user_data["dynamic_subject"] = subject
            await query.edit_message_text(
                f"Welche Zeit passt für {subject}?",
                reply_markup=keyboard_builder.build_dynamic_time_menu(subject),
            )
            await query.answer()
            return

        if data.startswith("plan_time_"):
            time_str = data.removeprefix("plan_time_")
            subject = context.user_data.get("dynamic_subject")
            if not subject:
                await query.answer("Bitte zuerst ein Fach wählen.", show_alert=True)
                return

            success = lernplan_service.add_dynamic_plan_entry(chat_id, subject, time_str)
            if not success:
                await query.answer("Diese Zeit ist bereits vorbei.", show_alert=True)
                return

            # Schedule the job
            if context.application:
                schedule_dynamic_job(context.application, chat_id, subject, time_str)

            confirmation = f"Geplant: {subject} um {time_str}. Ich erinnere dich rechtzeitig!"
            await query.edit_message_text(confirmation)
            await query.answer("Plan gespeichert!")
            context.user_data.pop("dynamic_subject", None)
            return

        if data == "use_joker":
            if lernplan_service.use_joker(chat_id):
                await query.edit_message_text("Genieß den Tag! ☀️ Joker eingesetzt.")
                await query.answer("Joker genutzt!")
            else:
                await query.answer("Keine Joker verfügbar.", show_alert=True)
            return

        # Week planning
        if data.startswith("plan_day_"):
            weekday = data.removeprefix("plan_day_")
            context.user_data["plan_weekday"] = weekday
            await query.edit_message_text(
                f"Fach für {weekday.capitalize()} wählen:",
                reply_markup=keyboard_builder.build_subject_menu(weekday),
            )
            await query.answer()
            return

        if data.startswith("plan_subject_") and data.count("_") == 3:
            # Week planning subject selection
            parts = data.split("_", 3)
            weekday = parts[2]
            subject = parts[3]
            context.user_data["plan_subject"] = subject
            context.user_data["plan_weekday"] = weekday
            await query.edit_message_text(
                f"Minuten für {weekday.capitalize()} – {subject} wählen:",
                reply_markup=keyboard_builder.build_minutes_menu(weekday, subject),
            )
            await query.answer()
            return

        if data.startswith("plan_minutes_custom_"):
            parts = data.split("_", 4)
            weekday = parts[3]
            subject = parts[4]
            context.user_data["awaiting_minutes"] = (weekday, subject)
            await query.edit_message_text(
                f"Eigene Minutenanzahl für {weekday.capitalize()} – {subject} eingeben "
                f"(Zahl {config.min_minutes}-{config.max_minutes}):"
            )
            await query.answer()
            return

        if data.startswith("plan_minutes_") and not data.startswith("plan_minutes_custom_"):
            parts = data.split("_", 4)
            weekday = parts[2]
            subject = parts[3]
            minutes = int(parts[4])

            lernplan_service.update_day_plan(
                chat_id, weekday, subject, minutes, config.student_chat_id, config.parent_chat_id
            )
            schedule_all_reminders(context.application)

            await query.edit_message_text(
                f"Gespeichert: {weekday.capitalize()} – {subject} ({minutes} Minuten)",
                reply_markup=keyboard_builder.build_weekday_menu(),
            )
            await query.answer("Gespeichert")
            return

    except Exception as e:
        LOGGER.error(f"Error handling callback {data}: {e}", exc_info=True)
        await query.answer("Ein Fehler ist aufgetreten.", show_alert=True)

    await query.answer()


async def on_learned_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle learned_yes/learned_no callbacks from daily check."""
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    data = query.data

    LOGGER.info(f"on_learned_response: Received '{data}' from chat {query.message.chat_id}")

    try:
        if data == "learned_yes":
            img = message_builder.get_random_happy_image()
            await query.edit_message_text("Super! Weiter so! 🐴🎉")
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=img)
            LOGGER.info(f"Sent positive response to chat {query.message.chat_id}")

            if config.parent_chat_id and config.parent_chat_id != query.message.chat_id:
                await context.bot.send_message(
                    chat_id=config.parent_chat_id, text="Antwort Schüler: JA gelernt ✅"
                )
                LOGGER.info(f"Sent YES notification to parent {config.parent_chat_id}")

        elif data == "learned_no":
            gif = message_builder.get_random_sad_gif()
            await query.edit_message_text("Vielleicht klappt es morgen besser. 🐴")
            await context.bot.send_animation(chat_id=query.message.chat_id, animation=gif)
            LOGGER.info(f"Sent negative response to chat {query.message.chat_id}")

            if config.parent_chat_id and config.parent_chat_id != query.message.chat_id:
                await context.bot.send_message(
                    chat_id=config.parent_chat_id, text="Antwort Schüler: NEIN gelernt ❌"
                )
                LOGGER.info(f"Sent NO notification to parent {config.parent_chat_id}")

    except Exception as e:
        LOGGER.error(f"Error handling learned response '{data}': {e}", exc_info=True)


# ============================================================================
# Text and Voice Handlers
# ============================================================================


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free text input."""
    if not update.message:
        return
    
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()

    # Handle menu button
    if text == "📋 Menü":
        await update.message.reply_text(
            "Hauptmenü:", reply_markup=keyboard_builder.build_main_menu()
        )
        return

    # Handle awaiting custom minutes input
    if "awaiting_minutes" in context.user_data:
        weekday, subject = context.user_data.pop("awaiting_minutes")
        try:
            minutes_value = int(text)
            if not (config.min_minutes <= minutes_value <= config.max_minutes):
                raise ValueError("Minutes out of range")
        except (ValueError, AttributeError):
            await update.message.reply_text(message_builder.get_funny_number_error())
            return

        lernplan_service.update_day_plan(
            chat_id, weekday, subject, minutes_value, 
            config.student_chat_id, config.parent_chat_id
        )
        schedule_all_reminders(context.application)
        
        await update.message.reply_text(
            f"Gespeichert: {weekday.capitalize()} – {subject} ({minutes_value} Minuten).",
            reply_markup=keyboard_builder.get_main_keyboard(),
        )
        return

    await update.message.reply_text(message_builder.get_funny_error())


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages from student to mark tasks as complete."""
    message = update.message
    if not message or not message.voice:
        return

    chat_id = message.chat_id
    if chat_id != config.student_chat_id:
        return

    settings = repo.load(chat_id)
    
    # Forward to parent
    forwarded = False
    if config.parent_chat_id:
        try:
            await context.bot.send_voice(
                chat_id=config.parent_chat_id,
                voice=message.voice.file_id,
                caption="🎙️ Sprachnachricht vom Schüler",
            )
            forwarded = True
        except Exception as exc:
            LOGGER.error(f"Failed to forward voice message: {exc}")

    # Mark most recent incomplete entry as complete
    now = datetime.now(timezone)
    today_iso = now.date().isoformat()
    now_time = now.time()

    past_candidate = None
    past_candidate_time = None

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

    if past_candidate:
        past_candidate["completed"] = True
        repo.save(settings)

    if forwarded:
        await message.reply_text("✅ Nachricht weitergeleitet und Plan aktualisiert.")
    else:
        await message.reply_text("✅ Plan aktualisiert.")


# ============================================================================
# Scheduled Jobs
# ============================================================================


async def morning_planning_prompt(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send morning planning prompt at configured time."""
    LOGGER.info("morning_planning_prompt: Starting morning prompt")

    if not config.student_chat_id:
        LOGGER.warning("morning_planning_prompt: STUDENT_CHAT_ID not set")
        return

    try:
        jokers_left = lernplan_service.get_jokers_available(config.student_chat_id)
        keyboard = keyboard_builder.build_morning_planning_keyboard(jokers_left)

        await context.bot.send_message(
            chat_id=config.student_chat_id,
            text="Guten Morgen! ☀️ Plan für heute?",
            reply_markup=keyboard,
        )
        LOGGER.info(f"Prompt sent to student (jokers={jokers_left})")
    except Exception as e:
        LOGGER.error(f"morning_planning_prompt: Failed to send prompt: {e}", exc_info=True)


async def daily_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily check at configured time (default 20:00)."""
    LOGGER.info("daily_check: Starting daily check")

    if not config.student_chat_id:
        LOGGER.warning("daily_check: STUDENT_CHAT_ID not set")
        return

    try:
        settings = repo.load(config.student_chat_id)
        now_dt = datetime.now(timezone)
        today = WEEKDAYS[now_dt.weekday()]
        today_iso = now_dt.date().isoformat()

        # Get today's dynamic entries
        todays_entries = [
            entry for entry in settings.daily_dynamic_plan 
            if entry.get("date_iso") == today_iso
        ]

        # Sort by time
        def sort_key(entry: dict) -> int:
            time_str = entry.get("time_str", "")
            try:
                hh, mm = map(int, time_str.split(":"))
                return hh * 60 + mm
            except (ValueError, TypeError):
                return 24 * 60 + 1

        todays_entries_sorted = sorted(todays_entries, key=sort_key)
        completed_count = sum(1 for entry in todays_entries_sorted if entry.get("completed"))

        # Build report
        report_text = message_builder.build_daily_report(
            todays_entries_sorted, completed_count, now_dt.strftime("%d.%m.%Y")
        )

        # Check if there was a plan for today
        day_plan = settings.week_plan.get(today)
        if day_plan:
            text = "Hast du heute auch gelernt?"
        else:
            text = "Heute war kein Lernplan-Eintrag hinterlegt – hast du trotzdem gelernt?"

        keyboard = keyboard_builder.build_learned_response_keyboard()

        await context.bot.send_message(
            chat_id=config.student_chat_id, text=text, reply_markup=keyboard
        )
        LOGGER.info("Successfully sent question to student")

        # Notify parent
        if config.parent_chat_id and config.parent_chat_id != config.student_chat_id:
            await context.bot.send_message(
                chat_id=config.parent_chat_id,
                text="(Info) 20-Uhr-Abfrage an Schüler gesendet.",
            )
            await context.bot.send_message(chat_id=config.parent_chat_id, text=report_text)
            LOGGER.info("Sent notifications to parent")

        # Clear dynamic plan
        settings.daily_dynamic_plan = []
        repo.save(settings)
        LOGGER.info("Cleared dynamic plan entries for next day")

    except Exception as e:
        LOGGER.error(f"daily_check: Error during daily check: {e}", exc_info=True)


async def dynamic_plan_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job to send reminder for dynamic plan entry."""
    job_data = context.job.data or {}
    chat_id = job_data.get("chat_id")
    subject = job_data.get("subject")
    time_str = job_data.get("time_str")
    
    if not chat_id or not subject or not time_str:
        LOGGER.warning(f"dynamic_plan_job: Missing job data {job_data}")
        return

    try:
        await context.bot.send_message(
            chat_id=chat_id, text=f"🔔 Zeit für {subject} um {time_str}! Viel Erfolg!"
        )
        LOGGER.info(f"Sent dynamic reminder for {subject} to {chat_id}")
    except Exception as e:
        LOGGER.error(f"dynamic_plan_job: Failed to send reminder: {e}", exc_info=True)


def schedule_dynamic_job(app: Application, chat_id: int, subject: str, time_str: str) -> bool:
    """Schedule a dynamic plan reminder job."""
    try:
        hh, mm = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        LOGGER.warning(f"Invalid time string '{time_str}' for chat {chat_id}")
        return False

    now_dt = datetime.now(timezone)
    target_dt = datetime.combine(now_dt.date(), time(hour=hh, minute=mm), tzinfo=timezone)
    
    if target_dt <= now_dt:
        LOGGER.info(f"Skipping past time {time_str} for chat {chat_id}")
        return False

    safe_subject = abs(hash(subject)) % 10000
    job_name = f"dynamic_{chat_id}_{hh:02d}{mm:02d}_{safe_subject}"
    
    # Remove existing job with same name
    for job in app.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()

    app.job_queue.run_once(
        dynamic_plan_job,
        when=target_dt,
        name=job_name,
        data={"chat_id": chat_id, "subject": subject, "time_str": time_str},
    )
    LOGGER.info(f"Scheduled {subject} for chat {chat_id} at {time_str}")
    return True


def schedule_all_reminders(app: Application) -> None:
    """Schedule all reminder jobs (morning prompt, daily check, dynamic plans)."""
    LOGGER.info("schedule_all_reminders: Starting job scheduling")

    # Remove only dynamic plan jobs, not system jobs
    job_count = 0
    for job in list(app.job_queue.jobs()):
        if job.name and job.name.startswith("dynamic_"):
            job.schedule_removal()
            job_count += 1
    LOGGER.info(f"Removed {job_count} existing dynamic jobs")

    # Schedule dynamic plans for today
    dynamic_count = 0
    today = datetime.now(timezone)
    today_iso = today.date().isoformat()
    
    for uid in repo.list_user_ids():
        settings = repo.load(uid)
        todays_entries = [
            entry for entry in settings.daily_dynamic_plan 
            if entry.get("date_iso") == today_iso
        ]
        
        # Clean old entries
        if len(todays_entries) != len(settings.daily_dynamic_plan):
            settings.daily_dynamic_plan = todays_entries
            repo.save(settings)

        for entry in todays_entries:
            if entry.get("completed"):
                continue
            subject = entry.get("subject")
            time_str = entry.get("time_str")
            if subject and time_str:
                if schedule_dynamic_job(app, uid, subject, time_str):
                    dynamic_count += 1

    LOGGER.info(f"Scheduled {dynamic_count} dynamic plan reminders")

    # Schedule system jobs (only once)
    # Check if already scheduled
    has_morning = any(
        job.name == "morning_planning_prompt" for job in app.job_queue.jobs()
    )
    has_daily = any(job.name == "daily_check_20" for job in app.job_queue.jobs())

    if not has_morning:
        morning_time = config.morning_prompt_time.split(":")
        app.job_queue.run_daily(
            morning_planning_prompt,
            time=time(hour=int(morning_time[0]), minute=int(morning_time[1]), tzinfo=timezone),
            name="morning_planning_prompt",
        )
        LOGGER.info(f"Scheduled morning_planning_prompt at {config.morning_prompt_time}")

    if not has_daily:
        daily_time = config.daily_check_time.split(":")
        app.job_queue.run_daily(
            daily_check,
            time=time(hour=int(daily_time[0]), minute=int(daily_time[1]), tzinfo=timezone),
            name="daily_check_20",
        )
        LOGGER.info(f"Scheduled daily_check at {config.daily_check_time}")

    LOGGER.info(f"Configuration: STUDENT={config.student_chat_id}, PARENT={config.parent_chat_id}")


# ============================================================================
# Application Setup
# ============================================================================


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    LOGGER.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    # Try to notify user
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "🤖 Ein Fehler ist aufgetreten. Bitte versuche es erneut."
            )
        except Exception:
            pass


def build_app() -> Application:
    """Build and configure the application."""
    if not config.telegram_token or config.telegram_token == "YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "TELEGRAM_TOKEN not set or invalid. Please configure userconfig/bot_config.json "
            "or set TELEGRAM_TOKEN environment variable."
        )
    
    app = ApplicationBuilder().token(config.telegram_token).build()
    
    # Add handlers
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
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Schedule jobs
    schedule_all_reminders(app)
    
    return app


def main() -> None:
    """Main entry point."""
    # Load configuration first
    cfg = load_config()
    
    # Setup logging with configured level
    setup_logging(cfg.log_level)
    
    # Initialize global instances
    init_globals(cfg)
    
    LOGGER.info("=" * 60)
    LOGGER.info("Lernplan Reminder Bot v2 Starting")
    LOGGER.info("=" * 60)
    LOGGER.info(f"Student Chat ID: {config.student_chat_id}")
    LOGGER.info(f"Parent Chat ID: {config.parent_chat_id}")
    LOGGER.info(f"Timezone: {config.timezone}")
    LOGGER.info(f"Allowed Subjects: {', '.join(config.get_subject_names())}")
    LOGGER.info("=" * 60)

    # Validate configuration
    if not config.student_chat_id:
        LOGGER.warning("⚠️  STUDENT_CHAT_ID is not set - daily check will not work!")
    if not config.parent_chat_id:
        LOGGER.warning("⚠️  PARENT_CHAT_ID is not set - parent notifications will not work!")

    # Build and run
    app = build_app()
    LOGGER.info("Bot started successfully. Polling for updates...")
    app.run_polling()


if __name__ == "__main__":
    main()
