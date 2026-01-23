from models.settings import DayPlan, SettingsRepository, UserSettings


def test_user_settings_roundtrip(tmp_path):
    repo = SettingsRepository(tmp_path)
    us = UserSettings(
        chat_id=123, reminder_times=["08:00"], week_plan={"montag": DayPlan("Mathe", 30)}
    )
    repo.save(us)
    loaded = repo.load(123)
    assert loaded.chat_id == 123
    assert loaded.reminder_times == ["08:00"]
    assert loaded.week_plan["montag"].subject == "Mathe"


def test_list_user_ids(tmp_path):
    repo = SettingsRepository(tmp_path)
    for cid in [1, 2, 3]:
        repo.save(UserSettings(chat_id=cid))
    ids = sorted(repo.list_user_ids())
    assert ids == [1, 2, 3]
