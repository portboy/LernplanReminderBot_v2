"""Test the shared reminder times and weekly overview functionality."""

from models.settings import DayPlan, SettingsRepository, UserSettings


def test_sync_reminder_times(tmp_path):
    """Test the sync_reminder_times function."""
    from unittest.mock import patch

    repo = SettingsRepository(tmp_path)

    # Create settings for two users
    settings1 = UserSettings(chat_id=123, reminder_times=["08:00"])
    settings2 = UserSettings(chat_id=456, reminder_times=["09:00"])
    repo.save(settings1)
    repo.save(settings2)

    with patch("bot.main.get_shared_chat_ids", return_value=[123, 456]):
        with patch("bot.main.repo", repo):
            from bot.main import sync_reminder_times

            sync_reminder_times(["10:00", "18:00"])

            # Check both users have the same times
            loaded1 = repo.load(123)
            loaded2 = repo.load(456)
            assert loaded1.reminder_times == ["10:00", "18:00"]
            assert loaded2.reminder_times == ["10:00", "18:00"]


def test_build_weekly_overview_basic(tmp_path):
    """Test the build_weekly_overview function with basic functionality."""
    from unittest.mock import patch

    repo = SettingsRepository(tmp_path)

    # Create a settings with some week plan
    settings = UserSettings(
        chat_id=456,
        reminder_times=["08:00", "18:00"],
        week_plan={"montag": DayPlan("Mathe", 30), "mittwoch": DayPlan("Englisch", 45)},
    )
    repo.save(settings)

    # Test the overview generation by directly using the repo
    with patch("bot.main.STUDENT_CHAT_ID", 456):
        with patch("bot.main.PARENT_CHAT_ID", 0):
            with patch("bot.main.repo", repo):
                with patch("bot.main.get_shared_chat_ids", return_value=[456]):
                    with patch(
                        "bot.main.get_shared_reminder_times", return_value=["08:00", "18:00"]
                    ):
                        from bot.main import build_weekly_overview

                        overview = build_weekly_overview(456)

                        # Check that it contains the expected information
                        assert "WOCHENÜBERSICHT" in overview
                        assert "Tag" in overview
                        assert "Fach" in overview
                        assert "Zeit" in overview
                        assert "Montag" in overview and "Mathe" in overview and "30min" in overview
                        assert (
                            "Mittwoch" in overview
                            and "Englisch" in overview
                            and "45min" in overview
                        )
                        assert "---" in overview  # For unset days
                        assert "ZUSAMMENFASSUNG" in overview
                        assert "ERINNERUNGSZEITEN" in overview
                        assert "08:00" in overview and "18:00" in overview


def test_user_settings_roundtrip_basic(tmp_path):
    """Basic test to ensure our changes don't break existing functionality."""
    repo = SettingsRepository(tmp_path)
    us = UserSettings(
        chat_id=123, reminder_times=["08:00"], week_plan={"montag": DayPlan("Mathe", 30)}
    )
    repo.save(us)
    loaded = repo.load(123)
    assert loaded.chat_id == 123
    assert loaded.reminder_times == ["08:00"]
    assert loaded.week_plan["montag"].subject == "Mathe"


def test_sync_week_plan(tmp_path):
    """Test the sync_week_plan function."""
    from unittest.mock import patch

    repo = SettingsRepository(tmp_path)

    # Create settings for two users with different plans
    settings1 = UserSettings(chat_id=123, week_plan={"montag": DayPlan("Mathe", 30)})
    settings2 = UserSettings(chat_id=456, week_plan={"montag": DayPlan("Englisch", 45)})
    repo.save(settings1)
    repo.save(settings2)

    with patch("bot.main.get_shared_chat_ids", return_value=[123, 456]):
        with patch("bot.main.repo", repo):
            from bot.main import sync_week_plan

            # Sync new plan
            new_plan = {"montag": DayPlan("Deutsch", 60), "dienstag": DayPlan("Mathe", 40)}
            sync_week_plan(new_plan)

            # Check both users have the same plan
            loaded1 = repo.load(123)
            loaded2 = repo.load(456)
            assert loaded1.week_plan["montag"].subject == "Deutsch"
            assert loaded1.week_plan["montag"].minutes == 60
            assert loaded2.week_plan["montag"].subject == "Deutsch"
            assert loaded2.week_plan["montag"].minutes == 60
            assert "dienstag" in loaded1.week_plan
            assert "dienstag" in loaded2.week_plan
