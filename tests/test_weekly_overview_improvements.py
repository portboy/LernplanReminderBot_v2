"""Tests for weekly overview and statistics (against new architecture)."""

from zoneinfo import ZoneInfo

from core.config import BotConfig, SubjectConfig
from models.settings import DayPlan, SettingsRepository, UserSettings
from services import LernplanService
from ui.messages import MessageBuilder

TZ = ZoneInfo("Europe/Berlin")


def _make_config(**overrides) -> BotConfig:
    defaults = dict(
        telegram_token="test_token",
        allowed_subjects=[
            SubjectConfig(name="Mathe", emoji="🔢"),
            SubjectConfig(name="Englisch", emoji="🇬🇧"),
            SubjectConfig(name="Deutsch", emoji="📝"),
        ],
    )
    defaults.update(overrides)
    return BotConfig(**defaults)


def test_weekly_overview_formatting():
    """Overview contains expected formatting elements."""
    cfg = _make_config()
    mb = MessageBuilder(cfg, TZ)

    week_plan = {
        "montag": DayPlan("Mathe", 30),
        "mittwoch": DayPlan("Englisch", 45),
    }
    reminder_times = ["08:00", "16:00"]

    overview = mb.build_weekly_overview(week_plan, reminder_times)

    assert "📊 **WOCHENÜBERSICHT**" in overview
    assert "📈 **ZUSAMMENFASSUNG**" in overview
    assert "⏰ **ERINNERUNGSZEITEN**" in overview
    assert "Montag" in overview
    assert "Mathe" in overview
    assert "30min" in overview
    assert "Mittwoch" in overview
    assert "Englisch" in overview
    assert "45min" in overview
    assert "08:00" in overview
    assert "16:00" in overview
    assert "2/7" in overview  # planned days


def test_time_display_with_hours():
    """Long study times are displayed in hours and minutes."""
    cfg = _make_config()
    mb = MessageBuilder(cfg, TZ)

    week_plan = {
        "montag": DayPlan("Mathe", 90),
        "dienstag": DayPlan("Englisch", 120),
        "mittwoch": DayPlan("Deutsch", 45),
    }

    overview = mb.build_weekly_overview(week_plan, ["09:00"])

    # 90+120+45 = 255 = 4h 15min
    assert "4h 15min" in overview


def test_empty_week_display():
    """Empty plan shows zero state."""
    cfg = _make_config()
    mb = MessageBuilder(cfg, TZ)

    overview = mb.build_weekly_overview({}, [])

    assert "0/7" in overview
    assert "0 Minuten" in overview
    assert "Keine Erinnerungszeiten" in overview


def test_weekly_statistics_empty(tmp_path):
    """Statistics with no history return zeros."""
    repo = SettingsRepository(tmp_path)
    repo.save(UserSettings(chat_id=100))

    svc = LernplanService(repo, TZ)
    stats = svc.get_weekly_statistics(100, days=7)

    assert stats["total_minutes"] == 0
    assert stats["days_learned"] == 0
    assert stats["subject_minutes"] == {}


def test_weekly_statistics_with_history(tmp_path):
    """Statistics count entries from learning_history."""
    repo = SettingsRepository(tmp_path)
    from datetime import date, timedelta

    today = date.today()
    repo.save(UserSettings(
        chat_id=100,
        week_plan={"montag": DayPlan("Mathe", 30)},
        learning_history=[
            {
                "date_iso": today.isoformat(),
                "weekday": "montag",
                "subject": "Mathe",
                "planned_minutes": 30,
                "source": "week_plan",
                "learned_response": "yes",
            },
            {
                "date_iso": (today - timedelta(days=1)).isoformat(),
                "weekday": "sonntag",
                "subject": "Englisch",
                "planned_minutes": 45,
                "source": "week_plan",
                "learned_response": "yes",
            },
        ],
    ))

    svc = LernplanService(repo, TZ)
    stats = svc.get_weekly_statistics(100, days=7)

    assert stats["total_minutes"] == 75
    assert stats["days_learned"] == 2
    assert stats["subject_minutes"]["Mathe"] == 30
    assert stats["subject_minutes"]["Englisch"] == 45


def test_weekly_statistics_excludes_no_response(tmp_path):
    """Entries with 'no' response and not completed are excluded."""
    repo = SettingsRepository(tmp_path)
    from datetime import date

    today = date.today()
    repo.save(UserSettings(
        chat_id=200,
        learning_history=[
            {
                "date_iso": today.isoformat(),
                "subject": "Mathe",
                "planned_minutes": 30,
                "learned_response": "no",
                "completed": False,
            },
        ],
    ))

    svc = LernplanService(repo, TZ)
    stats = svc.get_weekly_statistics(200, days=7)

    assert stats["total_minutes"] == 0


def test_statistics_message_builder():
    """Statistics message builder produces readable output."""
    cfg = _make_config()
    mb = MessageBuilder(cfg, TZ)

    stats = {
        "total_minutes": 120,
        "subject_minutes": {"Mathe": 75, "Englisch": 45},
        "days_learned": 3,
        "start_date": "21.02.2026",
        "end_date": "27.02.2026",
        "days": 7,
    }
    text = mb.build_weekly_statistics(stats)

    assert "WOCHEN-STATISTIK" in text
    assert "2h" in text  # 120 min = 2h
    assert "Mathe" in text
    assert "Englisch" in text
    assert "3/7" in text  # days learned


def test_reminder_time_icon():
    """Time icons match time of day."""
    cfg = _make_config()
    mb = MessageBuilder(cfg, TZ)

    assert "🌅" == mb.reminder_time_icon("07:00")
    assert "☀️" == mb.reminder_time_icon("12:00")
    assert "🌆" == mb.reminder_time_icon("18:00")
    assert "🌙" == mb.reminder_time_icon("22:00")
