# GitHub Copilot Instructions - LernplanReminderBot v2

## Projekt-Übersicht

**LernplanReminderBot v2** ist ein Telegram-Bot für Lernplanung und tägliche Erinnerungen.
Der Bot hilft Schülern, ihren Wochenplan zu organisieren und sendet automatische Erinnerungen.

### Technologie-Stack
- **Python 3.12** mit `python-telegram-bot` (v21.x)
- **Docker** für Containerisierung (Multi-stage Build)
- **GitHub Actions** für CI/CD
- **GitHub Container Registry (GHCR)** für Image-Hosting
- **Unraid Server** als Deployment-Ziel

## Deployment-Workflow

1. **Entwicklung**: Änderungen lokal oder im Workspace entwickeln
2. **Git Push**: Push zu GitHub (main/develop/feature-branches)
3. **GitHub Actions**: Automatischer Build und Push zu GHCR
   - Image-Tags: `branch-main`, `branch-develop`, `branch-<name>`, `sha-<hash>`
4. **Unraid Server**: Pull und Neustart des Containers
   ```bash
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Projektstruktur

```
src/
  bot/
    main_new.py          # Hauptbot-Logik (aktiv verwendet)
    main.py              # Legacy-Version
  core/
    config.py            # Bot-Konfiguration
    logging_config.py    # Logging-Setup
  models/
    settings.py          # Datenmodelle
  services/             # Business-Logik (Lernplan-Service, etc.)
  ui/
    keyboards.py         # Telegram Keyboards/Buttons
    messages.py          # Nachrichtentexte und Formatierung

userconfig/
  bot_config.json       # Laufzeit-Konfiguration (nicht in Git)

data/                   # User-Daten JSON-Dateien (nicht in Git)
```

## Wichtige Hinweise

### Container & Deployment
- **Zeitzone**: Immer `Europe/Berlin` verwenden (TZ env var + tzdata)
- **Non-root User**: Container läuft als `botuser` (UID 1000)
- **Volumes**: `/app/data` und `/app/userconfig` für Persistenz
- **Keine Ports**: Bot nutzt nur ausgehende Verbindungen zu Telegram

### Code-Konventionen
- **Logging**: Nutze `LOGGER` aus `logging_config.py`
- **Config**: Zugriff über `config` aus `core.config`
- **Async/Await**: Alle Bot-Handler sind async
- **Type Hints**: Immer verwenden für bessere Code-Qualität

### Bot-Architektur
- **Callback Query Handler**: Für Inline-Button-Interaktionen
- **Message Handler**: Für Textnachrichten und Sprachnachrichten
- **Context Data**: `context.user_data` für temporäre User-States
  - Beispiel: `awaiting_comment`, `awaiting_minutes`
- **Keyboards**: Über `KeyboardBuilder` in `ui/keyboards.py`

### Daten-Persistenz
- User-Daten in JSON-Dateien: `data/user_{chat_id}.json`
- Config in `userconfig/bot_config.json`
- **Keine Datenbank** - alles JSON-basiert

### Docker-Befehle
```bash
# Lokal entwickeln und testen
docker-compose up -d --build

# Production (nach GitHub Push)
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Logs anzeigen
docker-compose logs -f
```

## Häufige Aufgaben

### Neues Keyboard hinzufügen
1. Methode in `KeyboardBuilder` (`src/ui/keyboards.py`) erstellen
2. Handler in `main_new.py` implementieren
3. Callback-Data in Handler-Logik einbinden

### Neue Nachricht hinzufügen
1. Methode in `MessageBuilder` (`src/ui/messages.py`) erstellen
2. In entsprechendem Handler nutzen

### Config-Option hinzufügen
1. In `BotConfig` (`src/core/config.py`) definieren
2. In `userconfig/bot_config.json` als Standard setzen
3. Dokumentation in `CONFIG_GUIDE.md` aktualisieren

### Fehlersuche
- **Container-Logs**: `docker-compose logs -f`
- **Zeit-Probleme**: Prüfe TZ-Konfiguration in Docker-Files
- **Callback-Fehler**: Prüfe ob entsprechende Handler registriert sind
- **AttributeError bei Keyboards**: Prüfe ob Methode in `KeyboardBuilder` existiert

## Git-Workflow

- **main**: Production-ready Code
- **develop**: Entwicklungs-Branch für neue Features
- **feature/**: Feature-Branches für spezifische Änderungen

Alle Branches werden von GitHub Actions gebaut und zu GHCR gepusht.

## Wichtige Dateien

- `pyproject.toml`: Python-Dependencies
- `Dockerfile`: Container-Build (Multi-stage)
- `docker-compose.yml`: Lokale Entwicklung
- `docker-compose.prod.yml`: Production Deployment
- `.github/workflows/ci.yml`: GitHub Actions Workflow
- `CONFIG_GUIDE.md`: Konfigurations-Dokumentation
- `DEPLOYMENT.md`: Deployment-Anleitung

## Parent-Child Chat Feature

Der Bot unterstützt Parent-Child-Benachrichtigungen:
- Student erhält Erinnerungen und kann antworten
- Parent erhält Benachrichtigungen über Antworten und Kommentare
- Config: `student_chat_id` und `parent_chat_id` in `bot_config.json`

## Zeitplanung & Reminder

- Joker-System: Begrenzte Anzahl pro Woche
- Tägliche Erinnerungen basierend auf Wochenplan
- Flexible Zeitauswahl für dynamische Planung
- Wochenübersicht mit farbcodierten Status-Emojis
