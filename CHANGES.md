# Changelog

## v2.0.0 — Architektur-Refactoring (2026-02-27)

Vollständige Überarbeitung der Codebasis basierend auf dem Projekt-Audit (`PROJEKT_AUDIT_UND_KONZEPT.md`). Umsetzung aller kritischen Befunde aus Kapitel 2.3.

### Architektur

- **BotContext Dataclass** statt flacher Modul-Globaler. Alle Abhängigkeiten (Config, Repo, Service, Keyboards, Messages) gebündelt in `application.bot_data["ctx"]`, abrufbar per `get_ctx(context)`.
- **Service Layer** (`services/__init__.py`): Neue `LernplanService`-Klasse kapselt gesamte Business Logic (Sync, Reminder, History, Statistik). Handler rufen nur noch Service-Methoden auf statt direkt auf Repo zu schreiben.
- **UI-Module** aufgeteilt:
  - `ui/keyboards.py` — `KeyboardBuilder` für alle Telegram-Keyboards
  - `ui/messages.py` — `MessageBuilder` für alle Textformatierungen
- **Pydantic-Konfiguration** (`core/config.py`): `BotConfig` und `SubjectConfig` mit Validierung. Lädt aus `userconfig/bot_config.json` mit Env-Var-Override.
- **Legacy-Code entfernt**: Altes monolithisches `main.py` (1116 Zeilen) durch modulare Architektur ersetzt.

### Neue Features

- **⏰ Zeiten verwalten**: Grafischer Stunden-/Minutenpicker (Inline-Keyboards) statt Texteingabe. Bis zu 3 Erinnerungszeiten, synchron zwischen Schüler und Eltern.
- **📈 Wochen-Statistik**: Neues `learning_history`-Feld in `UserSettings`. Tägliche Antworten (Ja/Nein) werden dauerhaft archiviert. `get_weekly_statistics()` liest aus der Historie statt aus dem täglich gelöschten `daily_dynamic_plan`.
- **📊 Wochenübersicht**: Erweiterte Darstellung mit Farbcodes, Tages-Indikatoren, Gesamtzeit in h/min.
- **Wochen-Statistik Menü**: Neuer Button `📈 Wochen-Statistik` im Hauptmenü mit Fächeraufschlüsselung und Balkendiagramm.

### Stabilität & Sicherheit

- **Atomare JSON-Writes**: `SettingsRepository.save()` schreibt via `tempfile.mkstemp()` + `os.replace()` — kein Datenverlust bei Crash/Stromausfall.
- **Echter Health Check**: `src/healthcheck.py` prüft: Config ladbar, Data-Dir schreibbar, Telegram-API erreichbar (HTTP HEAD mit 5s Timeout).
- **Multi-Stage Docker Build**: Builder + Production Stage, Non-Root-User `botuser` (UID 1000), separate Volumes für `data/` und `userconfig/`.
- **Korrupte Datei bereinigt**: `data/user_67207672070553605536.json` entfernt.

### Dependency-Änderungen

- **Entfernt**: `pytz` — ersetzt durch `zoneinfo` (Stdlib ab Python 3.9)
- **Hinzugefügt**: `pydantic==2.8.2` — Konfigurationsvalidierung

### Konfiguration

- **Neue Methode**: `userconfig/bot_config.json` (im Container gemountet) statt `.env`-Datei.
- **Env-Var-Override**: `TELEGRAM_TOKEN`, `STUDENT_CHAT_ID`, `PARENT_CHAT_ID`, `TIMEZONE`, `LOG_LEVEL`, `DATA_DIR` überschreiben JSON-Werte.
- **Neue Config-Felder**: `allowed_subjects`, `dynamic_planning_times`, `duration_choices`, `max_reminder_times`, `morning_prompt_time`, `daily_check_time`, `jokers_per_week`, `horse_happy_images`, `sad_gifs`.

### Tests

- **Komplett migriert**: Alte Tests, die über Monkey-Patching `bot.main`-Globals testeten, durch neue Tests gegen `LernplanService` und `MessageBuilder` ersetzt.
- **29 Tests** in 3 Dateien:
  - `test_config.py` — BotConfig Validierung, SubjectConfig, load_config (JSON/Env)
  - `test_shared_functionality.py` — Reminder Sync, Week Plan Sync, History Persistenz
  - `test_weekly_overview_improvements.py` — Statistik, Messages, Zeitformatierung

### Dateistruktur (vorher → nachher)

| Vorher | Nachher | Änderung |
| :--- | :--- | :--- |
| `src/bot/main.py` (1116 Zeilen, monolithisch) | `src/bot/main.py` (907 Zeilen, modular) | Komplett neu geschrieben |
| — | `src/core/config.py` | Neu erstellt |
| — | `src/services/__init__.py` | Neu erstellt |
| — | `src/ui/keyboards.py` | Neu erstellt |
| — | `src/ui/messages.py` | Neu erstellt |
| — | `src/healthcheck.py` | Neu erstellt |
| `src/models/settings.py` | `src/models/settings.py` | `learning_history` + atomare Writes |
| `Dockerfile` (einzel-stage) | `Dockerfile` (multi-stage) | Security + Optimierung |
| `docker-compose.yml` (kein healthcheck) | `docker-compose.yml` | Healthcheck + userconfig Volume |
| `pyproject.toml` (pytz) | `pyproject.toml` | pytz entfernt, pydantic hinzugefügt |

---

## v1.x — Initiale Releases

### v1.2 — Shared Reminder Times & Weekly Overview

- Erinnerungszeiten synchron zwischen Schüler und Eltern
- Wochenübersicht als Menü-Option
- Neue Tests für geteilte Funktionalität

### v1.1 — Daily Reminder & Voice Forwarding

- Morning Prompt um 07:30
- 20:00-Uhr Tagescheck mit Ja/Nein
- Sprachnachrichten-Weiterleitung an Eltern
- Joker-System (1× pro Woche)

### v1.0 — Initial Release

- Grundlegende Bot-Funktionalität
- Wochenplan-Verwaltung
- JSON-Persistenz
- Docker-Deployment
