# Copilot Instructions — LernplanReminderBot v2

## Projektübersicht

Telegram-Bot (Python) zum Verwalten und Erinnern an tägliche Lernpläne für Schüler, mit Eltern-Synchronisation. Läuft als Docker-Container mit JSON-basierter Persistenz.

## Technologie-Stack

- **Python ≥ 3.11** (Zielversion im Container: 3.12)
- **python-telegram-bot 21.x** (async, v20+ API)
- **APScheduler 3.10.x** — Erinnerungen, Tagescheck, Wochenreset
- **Pydantic 2.x** — Konfigurationsvalidierung (`BotConfig`)
- **Dataclasses** — Domain-Modelle (`UserSettings`, `DayPlan`)
- **zoneinfo** (stdlib) — Zeitzonen, kein `pytz`
- **pytest** + **ruff** — Testing & Linting

## Architektur & Schichten

```
bot/main.py          → Telegram-Handler, BotContext, Scheduler-Jobs
services/__init__.py → LernplanService (Business Logic)
models/settings.py   → UserSettings, DayPlan, SettingsRepository (JSON-Persistenz)
ui/keyboards.py      → KeyboardBuilder (Telegram InlineKeyboards)
ui/messages.py       → MessageBuilder (Textformatierung)
core/config.py       → BotConfig (Pydantic), load_config()
core/logging_config  → setup_logging()
healthcheck.py       → Docker HEALTHCHECK
```

### Wichtige Patterns

- **BotContext** (Dataclass in `bot_data["ctx"]`) bündelt alle Abhängigkeiten — keine globalen Variablen.
- **`get_ctx(context)`** extrahiert den BotContext in jedem Handler.
- **Atomare JSON-Writes**: `tempfile` + `os.replace` in `SettingsRepository` — niemals direkt in User-Dateien schreiben.
- **Shared State**: Student und Parent teilen Wochenpläne und Erinnerungszeiten; Änderungen müssen für beide Chat-IDs synchronisiert werden.
- **Handler-Struktur**: Alle Telegram-Handler sind `async def` Funktionen mit Signatur `(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None`.

## Code-Konventionen

### Python-Stil

- `from __future__ import annotations` in jedem Modul.
- Type Hints verwenden: `int | None` (Union-Syntax), `list[str]`, `dict[str, Any]`.
- Docstrings: Dreifache Anführungszeichen, kurze einzeilige Beschreibung.
- `LOGGER = logging.getLogger(__name__)` pro Modul.
- Zeilenlänge: **100 Zeichen** (ruff-Konfiguration).
- Ruff-Regeln: `E`, `F`, `I` (isort), `B` (bugbear).
- Konstanten in UPPER_CASE (`WEEKDAYS`).

### Imports

```python
# 1. stdlib
from datetime import datetime
from zoneinfo import ZoneInfo

# 2. third-party
from telegram import Update, InlineKeyboardButton
from pydantic import BaseModel

# 3. project-intern (relative zum src/-Verzeichnis)
from core.config import BotConfig, load_config
from models.settings import SettingsRepository, WEEKDAYS
from services import LernplanService
from ui.keyboards import KeyboardBuilder
```

### Benennungen

- Module/Packages: `snake_case`
- Klassen: `PascalCase` (`BotContext`, `KeyboardBuilder`, `LernplanService`)
- Funktionen/Handler: `snake_case` (`daily_check`, `start`, `handle_callback`)
- Callback-Daten: `snake_case` mit Prefix (`menu_plan`, `pick_hour_14`, `learned_yes`)
- Wochentage: Kleingeschrieben auf Deutsch (`montag`, `dienstag`, ...)

## Konfiguration

- Primär über `userconfig/bot_config.json` (Pydantic-Validierung).
- Environment-Variablen überschreiben JSON-Werte (`TELEGRAM_TOKEN`, `LOG_LEVEL`, etc.).
- Pfade im Container: `/app/data/`, `/app/userconfig/`.
- Lokal: `data/`, `userconfig/`.

## Persistenz

- Ein JSON-File pro User: `data/user_<chat_id>.json`.
- Schema: `UserSettings.to_dict()` / `UserSettings.from_dict()`.
- Felder: `reminder_times`, `week_plan`, `jokers_available`, `daily_dynamic_plan`, `learning_history`.
- **Keine Datenbank** — nur Dateisystem.

## Tests

- Framework: **pytest** (Pfad: `tests/`).
- `pythonpath = ["src"]` in `pyproject.toml` — Imports wie im Produktionscode.
- Tests sollen `LernplanService`, `BotConfig`, `MessageBuilder` u.a. ohne Telegram-Mocking testen.
- Temporäre Dateien für SettingsRepository-Tests verwenden (`tmp_path` Fixture).

## Docker

- Multi-Stage Build: Builder → Production (python:3.12-slim).
- Non-Root User `botuser` (UID 1000).
- Volumes: `/app/data`, `/app/userconfig`.
- Entrypoint: `python -m bot.main`.
- Healthcheck: `python src/healthcheck.py`.

## Sprache

- **Code**: Englisch (Variablen, Funktionen, Docstrings, Logs).
- **User-facing Texte** (Telegram-Nachrichten, Buttons): **Deutsch**.
- **Kommentare / Dokumentation**: Deutsch ist akzeptiert.
- **Emoji**: Werden in UI-Texten und Message-Buildern aktiv eingesetzt.

## Wichtige Hinweise für Änderungen

1. Neue Business Logic gehört in `services/__init__.py` (`LernplanService`), nicht in Handler.
2. Neue Keyboards in `ui/keyboards.py`, neue Nachrichten-Texte in `ui/messages.py`.
3. Bei Änderungen an `UserSettings`-Feldern: `to_dict()`, `from_dict()` und die JSON-Dateien kompatibel halten (Rückwärtskompatibilität mit vorhandenen User-Daten).
4. Neue Konfigurationsoptionen in `BotConfig` mit sinnvollen Defaults hinzufügen.
5. Scheduler-Jobs in `bot/main.py` registrieren, Logic aber in Service auslagern.
6. Immer `ruff check` und `pytest` vor Commit ausführen.
