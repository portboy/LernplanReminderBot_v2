"""Test the improved weekly overview functionality."""

from unittest.mock import patch

from models.settings import DayPlan, SettingsRepository, UserSettings


def test_professional_overview_formatting(tmp_path):
    """Test that the professional overview has proper formatting elements."""
    repo = SettingsRepository(tmp_path)

    settings = UserSettings(
        chat_id=123,
        reminder_times=["08:00", "16:00"],
        week_plan={
            "montag": DayPlan("Mathematik", 30),
            "mittwoch": DayPlan("Englisch", 45),
        },
    )
    repo.save(settings)

    with patch("bot.main.repo", repo):
        with patch("bot.main.get_shared_chat_ids", return_value=[]):
            from bot.main import build_weekly_overview

            overview = build_weekly_overview(123)

            # Check professional formatting elements
            assert "📊 **WOCHENÜBERSICHT**" in overview
            assert "```" in overview  # Code block for table
            assert "┌─────────────┬─────────────┬────────┐" in overview  # Table border
            assert "📈 **ZUSAMMENFASSUNG**" in overview
            assert "⏰ **ERINNERUNGSZEITEN**" in overview

            # Check emojis are used for days
            assert "🔵" in overview or "🟢" in overview or "🟡" in overview

            # Check time formatting improvements
            assert "min" in overview
            assert "📅 Geplante Tage:" in overview


def test_time_display_with_hours(tmp_path):
    """Test that long study times are displayed in hours and minutes."""
    repo = SettingsRepository(tmp_path)

    settings = UserSettings(
        chat_id=456,
        reminder_times=["09:00"],
        week_plan={
            "montag": DayPlan("Mathe", 90),  # 1h 30min
            "dienstag": DayPlan("Englisch", 120),  # 2h
            "mittwoch": DayPlan("Deutsch", 45),  # 45min
        },
    )
    repo.save(settings)

    with patch("bot.main.repo", repo):
        with patch("bot.main.get_shared_chat_ids", return_value=[]):
            from bot.main import build_weekly_overview

            overview = build_weekly_overview(456)

            # Should show total time in hours and minutes format
            # (90+120+45 = 255 minutes = 4h 15min)
            assert "4h 15min" in overview


def test_empty_week_display(tmp_path):
    """Test display when no days are planned."""
    repo = SettingsRepository(tmp_path)

    settings = UserSettings(chat_id=789, reminder_times=[], week_plan={})
    repo.save(settings)

    with patch("bot.main.repo", repo):
        with patch("bot.main.get_shared_chat_ids", return_value=[]):
            from bot.main import build_weekly_overview

            overview = build_weekly_overview(789)

            # Check empty state is handled gracefully
            assert "0/7" in overview
            assert "0 Minuten" in overview
            assert "Keine Erinnerungszeiten" in overview
            assert "---" in overview  # For unset days


def test_interactive_menu_structure(tmp_path):
    """Test the interactive menu has proper button layout."""
    repo = SettingsRepository(tmp_path)

    settings = UserSettings(
        chat_id=123,
        week_plan={
            "montag": DayPlan("Mathe", 30),
            "mittwoch": DayPlan("Englisch", 45),
        },
    )
    repo.save(settings)

    with patch("bot.main.repo", repo):
        with patch("bot.main.get_shared_chat_ids", return_value=[]):
            from bot.main import build_overview_menu

            menu = build_overview_menu(123)

            # Should have multiple rows
            assert len(menu.inline_keyboard) >= 3

            # First two rows should be weekday buttons
            weekday_buttons = menu.inline_keyboard[0] + menu.inline_keyboard[1]
            assert len(weekday_buttons) == 7  # All 7 days

            # Check that planned days have different buttons than unplanned
            button_texts = [btn.text for btn in weekday_buttons]
            planned_buttons = [btn for btn in button_texts if "🟦" in btn or "🟨" in btn]
            unplanned_buttons = [btn for btn in button_texts if "➕" in btn]

            # Should have some of each type
            assert len(planned_buttons) > 0
            assert len(unplanned_buttons) > 0

            # Last row should have control buttons
            control_row = menu.inline_keyboard[-1]
            control_texts = [btn.text for btn in control_row]
            assert any("Aktualisieren" in text for text in control_texts)
            assert any("Zurück" in text for text in control_texts)


def test_reminder_time_icons(tmp_path):
    """Test that reminder times get appropriate time-of-day icons."""
    repo = SettingsRepository(tmp_path)

    settings = UserSettings(
        chat_id=123,
        reminder_times=["07:00", "12:00", "18:00", "22:00"],
        week_plan={"montag": DayPlan("Test", 30)},
    )
    repo.save(settings)

    with patch("bot.main.repo", repo):
        with patch("bot.main.get_shared_chat_ids", return_value=[]):
            from bot.main import build_weekly_overview

            overview = build_weekly_overview(123)

            # Should have time-appropriate icons
            assert "🌅" in overview  # Early morning (07:00)
            assert "☀️" in overview or "🌤️" in overview  # Noon/afternoon (12:00)
            assert "🌆" in overview  # Evening (18:00)
            assert "🌙" in overview  # Night (22:00)
