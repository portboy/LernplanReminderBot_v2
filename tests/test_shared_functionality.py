"""Tests for shared functionality (reminder times, week plan sync, learning history)."""

from models.settings import DayPlan, SettingsRepository, UserSettings
from services import LernplanService
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")


def test_sync_reminder_times(tmp_path):
    """Syncing reminder times updates both users."""
    repo = SettingsRepository(tmp_path)
    repo.save(UserSettings(chat_id=123, reminder_times=["08:00"]))
    repo.save(UserSettings(chat_id=456, reminder_times=["09:00"]))

    svc = LernplanService(repo, TZ)
    svc.sync_reminder_times(["10:00", "18:00"], student_id=123, parent_id=456)

    assert repo.load(123).reminder_times == ["10:00", "18:00"]
    assert repo.load(456).reminder_times == ["10:00", "18:00"]


def test_add_reminder_time(tmp_path):
    """Adding a reminder time succeeds and is validated."""
    repo = SettingsRepository(tmp_path)
    repo.save(UserSettings(chat_id=100))

    svc = LernplanService(repo, TZ)
    ok, msg = svc.add_reminder_time(100, "08:30", max_times=3, student_id=100, parent_id=None)
    assert ok
    assert "08:30" in msg

    assert "08:30" in repo.load(100).reminder_times


def test_add_reminder_time_duplicate(tmp_path):
    """Duplicate times are rejected."""
    repo = SettingsRepository(tmp_path)
    repo.save(UserSettings(chat_id=100, reminder_times=["08:30"]))

    svc = LernplanService(repo, TZ)
    ok, _ = svc.add_reminder_time(100, "08:30", max_times=3, student_id=100, parent_id=None)
    assert not ok


def test_add_reminder_time_max_reached(tmp_path):
    """Cannot exceed max reminder times."""
    repo = SettingsRepository(tmp_path)
    repo.save(UserSettings(chat_id=100, reminder_times=["08:00", "12:00", "18:00"]))

    svc = LernplanService(repo, TZ)
    ok, _ = svc.add_reminder_time(100, "20:00", max_times=3, student_id=100, parent_id=None)
    assert not ok


def test_remove_reminder_time(tmp_path):
    """Removing a reminder time works."""
    repo = SettingsRepository(tmp_path)
    repo.save(UserSettings(chat_id=100, reminder_times=["08:00", "18:00"]))

    svc = LernplanService(repo, TZ)
    ok, _ = svc.remove_reminder_time(100, "08:00", student_id=100, parent_id=None)
    assert ok
    assert repo.load(100).reminder_times == ["18:00"]


def test_sync_week_plan(tmp_path):
    """Syncing week plan updates both users."""
    repo = SettingsRepository(tmp_path)
    repo.save(UserSettings(chat_id=123, week_plan={"montag": DayPlan("Mathe", 30)}))
    repo.save(UserSettings(chat_id=456, week_plan={"montag": DayPlan("Englisch", 45)}))

    svc = LernplanService(repo, TZ)
    new_plan = {"montag": DayPlan("Deutsch", 60), "dienstag": DayPlan("Mathe", 40)}
    svc.sync_week_plan(new_plan, student_id=123, parent_id=456)

    loaded1 = repo.load(123)
    loaded2 = repo.load(456)
    assert loaded1.week_plan["montag"].subject == "Deutsch"
    assert loaded2.week_plan["montag"].subject == "Deutsch"
    assert "dienstag" in loaded1.week_plan
    assert "dienstag" in loaded2.week_plan


def test_user_settings_roundtrip(tmp_path):
    """Basic roundtrip: save → load preserves data."""
    repo = SettingsRepository(tmp_path)
    us = UserSettings(
        chat_id=123, reminder_times=["08:00"], week_plan={"montag": DayPlan("Mathe", 30)}
    )
    repo.save(us)
    loaded = repo.load(123)
    assert loaded.chat_id == 123
    assert loaded.reminder_times == ["08:00"]
    assert loaded.week_plan["montag"].subject == "Mathe"


def test_learning_history_persists(tmp_path):
    """Learning history is saved and loaded correctly."""
    repo = SettingsRepository(tmp_path)
    us = UserSettings(
        chat_id=42,
        learning_history=[
            {"date_iso": "2026-02-27", "subject": "Mathe", "completed": True},
        ],
    )
    repo.save(us)
    loaded = repo.load(42)
    assert len(loaded.learning_history) == 1
    assert loaded.learning_history[0]["subject"] == "Mathe"


def test_list_user_ids(tmp_path):
    """list_user_ids returns all persisted IDs."""
    repo = SettingsRepository(tmp_path)
    for cid in [1, 2, 3]:
        repo.save(UserSettings(chat_id=cid))
    assert sorted(repo.list_user_ids()) == [1, 2, 3]
