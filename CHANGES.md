# Changes Made for Issue: Shared Reminder Times and Weekly Overview

## Problem Statement (German)
- Die Erinnerungszeiten sollen für Schüler und Elternteil identisch sein, egal, wer die Zeit für die Erinnerung festgelegt hat.
- Zusätzlich man über das Menü noch eine Wochenübersicht erhalten, welches Fach aktuell mit welcher Zeit für welchen Tag festgelegt ist bzw. wo noch gar nix festgelegt ist.

## Translation
- Reminder times should be identical for student and parent, regardless of who set the reminder time.
- Additionally, one should be able to get a weekly overview through the menu showing which subject with which time is set for which day, or where nothing is set yet.

## Changes Implemented

### 1. Shared Reminder Times Functionality

**Files Modified:**
- `src/bot/main.py`

**New Functions Added:**
- `get_shared_chat_ids()`: Returns list of chat IDs that should share reminder times (PARENT_CHAT_ID and STUDENT_CHAT_ID)
- `sync_reminder_times(new_times)`: Synchronizes reminder times across all shared chat IDs
- `get_shared_reminder_times()`: Gets the current shared reminder times (prioritizes student settings)

**Modified Functions:**
- `zeiten_cmd()`: Now uses shared reminder times for parent/student chats
- `addzeit_cmd()`: Now synchronizes time additions across shared chats
- `delzeit_cmd()`: Now synchronizes time deletions across shared chats
- `build_times_menu()`: Updated to work with chat_id parameter instead of settings object
- `handle_callback()`: Updated to handle shared reminder times in menu interactions
- `handle_free_text()`: Updated to sync reminder times when adding via menu

### 2. Weekly Overview Menu Functionality

**Files Modified:**
- `src/bot/main.py`

**New Functions Added:**
- `build_weekly_overview(chat_id)`: Creates a formatted text showing the complete weekly plan and reminder times
- `build_overview_menu()`: Creates the inline keyboard for the weekly overview

**Modified Functions:**
- `build_main_menu()`: Added new "📊 Wochenübersicht" menu option
- `handle_callback()`: Added handler for "menu_overview" callback

**Menu Structure:**
The main menu now includes:
- ⏰ Zeiten verwalten (existing)
- 📅 Wochenplan bearbeiten (existing)
- 📊 Wochenübersicht (NEW)
- 🔄 Schließen (existing)

### 3. Weekly Overview Display Format
The weekly overview shows:
- Header: "📊 **Wochenübersicht**"
- Each day with either:
  - "**Montag:** Mathe (30 Min)" for configured days
  - "**Dienstag:** _(nicht festgelegt)_" for unconfigured days
- Footer showing current reminder times
- Back button to return to main menu

### 4. Testing
**New Test File:**
- `tests/test_shared_functionality.py`

**Tests Added:**
- `test_sync_reminder_times()`: Tests that reminder times sync correctly across chats
- `test_build_weekly_overview_basic()`: Tests weekly overview generation
- `test_user_settings_roundtrip_basic()`: Ensures existing functionality still works

## Behavior Changes

### For Student and Parent Users:

1. **Reminder Time Management:**
   - When either student or parent adds/removes reminder times, the change applies to both
   - Both users will see identical reminder times in their menus
   - Both users will receive reminders at the same times

2. **Weekly Overview:**
   - New menu option accessible to all users
   - Shows complete weekly plan with subjects and minutes
   - Shows current reminder times
   - Clearly indicates days without plans

### For Other Users:
- Non-student/parent users continue to have independent reminder times
- All users can access the weekly overview feature

## Technical Implementation Details

- Uses environment variables `STUDENT_CHAT_ID` and `PARENT_CHAT_ID` to identify shared accounts
- Reminder time synchronization happens immediately when times are modified
- Weekly overview prioritizes student settings for display (falls back to parent if student not configured)
- All existing functionality remains unchanged for users not configured as student/parent
- Maintains backward compatibility with existing data structures

## Files Changed
- `src/bot/main.py`: Major changes for shared functionality and weekly overview
- `src/models/settings.py`: Minor formatting fixes from linter
- `tests/test_shared_functionality.py`: New test file
- `tests/test_time_validation.py`: Minor formatting fixes from linter