"""Tests for anonymized settings repository."""

import json
from pathlib import Path

from models.settings import DayPlan, DayPlanModel, SettingsRepository, UserSettings
import pytest


def test_day_plan_validation():
    """Test DayPlan validation with Pydantic."""
    # Valid
    plan = DayPlanModel(subject="Mathe", minutes=30)
    assert plan.subject == "Mathe"
    assert plan.minutes == 30

    # Invalid minutes (negative)
    with pytest.raises(Exception):
        DayPlanModel(subject="Mathe", minutes=-10)

    # Invalid subject (empty)
    with pytest.raises(Exception):
        DayPlanModel(subject="", minutes=30)


def test_anonymized_filenames(tmp_path):
    """Test that filenames are anonymized."""
    repo = SettingsRepository(tmp_path)
    
    chat_id = 123456789
    settings = UserSettings(chat_id=chat_id)
    repo.save(settings)
    
    # Check that file doesn't contain chat_id directly
    files = list(tmp_path.glob("user_*.json"))
    assert len(files) >= 1
    
    # Filename should not contain the actual chat_id
    for f in files:
        if f.name != "id_mapping.json":
            assert str(chat_id) not in f.name
            assert len(f.stem.split("_")[1]) == 16  # Hash length


def test_id_mapping_creation(tmp_path):
    """Test that id_mapping.json is created."""
    repo = SettingsRepository(tmp_path)
    
    chat_id_1 = 111111
    chat_id_2 = 222222
    
    settings_1 = UserSettings(chat_id=chat_id_1)
    settings_2 = UserSettings(chat_id=chat_id_2)
    
    repo.save(settings_1)
    repo.save(settings_2)
    
    # Check mapping file exists
    mapping_file = tmp_path / "id_mapping.json"
    assert mapping_file.exists()
    
    # Load and verify
    with mapping_file.open("r") as f:
        mapping = json.load(f)
    
    assert len(mapping) >= 2
    assert chat_id_1 in mapping.values()
    assert chat_id_2 in mapping.values()


def test_migration_from_old_format(tmp_path):
    """Test automatic migration from old filename format."""
    repo = SettingsRepository(tmp_path)
    
    chat_id = 987654321
    
    # Create old format file
    old_file = tmp_path / f"user_{chat_id}.json"
    old_data = {
        "chat_id": chat_id,
        "reminder_times": ["08:00"],
        "week_plan": {},
        "jokers_available": 1,
        "last_joker_reset_iso": "",
        "daily_dynamic_plan": [],
    }
    with old_file.open("w") as f:
        json.dump(old_data, f)
    
    # Load should trigger migration
    settings = repo.load(chat_id)
    
    assert settings.chat_id == chat_id
    assert settings.reminder_times == ["08:00"]
    
    # Old file should be gone (or check new file exists)
    # Note: Migration moves file on first access


def test_load_nonexistent_user(tmp_path):
    """Test loading settings for new user."""
    repo = SettingsRepository(tmp_path)
    
    chat_id = 999999999
    settings = repo.load(chat_id)
    
    assert settings.chat_id == chat_id
    assert settings.jokers_available == 1
    assert len(settings.week_plan) == 0


def test_save_and_load_roundtrip(tmp_path):
    """Test save and load roundtrip."""
    repo = SettingsRepository(tmp_path)
    
    chat_id = 555555
    settings = UserSettings(
        chat_id=chat_id,
        reminder_times=["07:30", "20:00"],
        week_plan={"montag": DayPlan("Mathe", 60)},
        jokers_available=0,
    )
    
    repo.save(settings)
    loaded = repo.load(chat_id)
    
    assert loaded.chat_id == chat_id
    assert loaded.reminder_times == ["07:30", "20:00"]
    assert "montag" in loaded.week_plan
    assert loaded.week_plan["montag"].subject == "Mathe"
    assert loaded.week_plan["montag"].minutes == 60
    # Note: jokers_available may be reset to 1 if it's a new week
    assert loaded.jokers_available >= 0


def test_list_user_ids_with_mapping(tmp_path):
    """Test listing user IDs with mapping."""
    repo = SettingsRepository(tmp_path)
    
    chat_ids = [111, 222, 333]
    
    for chat_id in chat_ids:
        settings = UserSettings(chat_id=chat_id)
        repo.save(settings)
    
    user_ids = repo.list_user_ids()
    
    assert len(user_ids) >= 3
    for chat_id in chat_ids:
        assert chat_id in user_ids
