# Lernplan Reminder Bot v2

Lernplan Reminder Bot v2 ist die komplette Neugestaltung des früheren Lernplan-Reminder-Bots. Die neue Version setzt auf eine gemeinsame Eltern-Schüler-Erfahrung, Inline- und Reply-Menüs, grafische Zeitpicker sowie `python-telegram-bot`-gestützte Scheduler-Jobs, um tägliche Erinnerungen zuverlässig auszuliefern.

## Highlights der Version 2

- **Shared experience:** Eltern und Schüler sehen denselben Wochenplan, identische Erinnerungszeiten und erhalten dieselben Benachrichtigungen.
- **Inline- und Reply-Menüs:** Ein permanenter Menü-Button (📋) plus Inline-Keyboards führen durch Plan-Updates, Zeiten und Übersichten ohne zusätzliche Texteingaben.
- **Grafische Zeitauswahl:** Komfortable Stunden-/Minuten-Picker und farbcodierte Emojis in der Wochenübersicht machen das Einstellen der Lernzeiten interaktiv.
- **Scheduling & Jobs:** `apscheduler` und die `JobQueue` stellen tägliche 20:00-Reminder, regelmäßige Checks und Test-Reminders sicher.
- **Persistenz:** Nutzer werden unter `data/user_<chat_id>.json` gespeichert; so lassen sich Chat-IDs direkt aus den Dateinamen ablesen.
- **Container-Ready:** Dockerfile, docker-compose-Vorlagen und GHCR-Images erlauben schnelle Deployments auf Servern, Unraid oder lokal im Headless-Modus.

## Repository-Layout

- `bot/main.py` – Einstiegspunkt; `python -m bot.main` startet die Telegram-Polling-Schleife und Scheduler.
- `core/logging_config.py` – zentrale Logging-Konfiguration mit konsistenten Formatter- und Handler-Einstellungen.
- `models/settings.py` – liest `.env` und stellt die erwarteten Variablen für den Rest der App bereit.
- `data/` – automatisch erzeugte JSON-Dateien pro Chat (Parent/Student).
- `userconfig/.env` – Beispielkonfiguration für lokale Tests.
- `tests/` – Pytest-Suite für gemeinsam genutzte Funktionen.

## Voraussetzungen

- Python 3.11+
- Telegram-Bot-Token vom BotFather
- Optional: Docker/Docker Compose / Unraid für Containerbetrieb

## Schnellstart (lokal)

1. Repository klonen oder per ZIP herunterladen.
2. Virtuelle Umgebung und Abhängigkeiten installieren:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```
3. `.env` konfigurieren:
   ```bash
   cp userconfig/.env .env
   # TELEGRAM_TOKEN, STUDENT_CHAT_ID und PARENT_CHAT_ID ergänzen
   ```
4. Bot starten:
   ```bash
   set -a
   source .env
   set +a
   python -m bot.main
   ```

   Beim Start wird die Konfiguration eingelesen, `daily_check` geplant und der Telegram-Polling-Loop aktiviert.

## Docker Build & Run (lokal)

```bash
docker build -t lernplan-reminder-bot-v2 .
cp userconfig/.env .env  # echtes Token und Chat-IDs einsetzen

docker run -d --name lernplan-reminder-bot-v2 --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  lernplan-reminder-bot-v2
```

Alternativ:
```bash
docker compose up -d --build
```

## Unraid-Deployment

1. AppData-Verzeichnis anlegen:
   ```bash
   mkdir -p /mnt/user/appdata/LernplanReminderBot_v2/data
   ```
2. `.env` mit Token und Chat-IDs füllen.
3. Container starten (GHCR oder lokal gebaut):
   ```bash
docker run -d \
  --name lernplan-reminder-bot-v2 \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot_v2/.env \
  -v /mnt/user/appdata/LernplanReminderBot_v2/data:/app/data \
  ghcr.io/portboy/lernplan-reminder-bot-v2:latest
```

Weitere Deployment-Varianten (lokale Builds, `docker-compose.prod.yml` usw.) stehen in der **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Environment-Variablen

| Variable | Bedeutung |
|----------|-----------|
| `TELEGRAM_TOKEN` | Token vom BotFather |
| `LOG_LEVEL` | z. B. INFO oder DEBUG |
| `DATA_DIR` | Verzeichnis für JSON-Dateien (Standard: `data`) |
| `PARENT_CHAT_ID` | Eltern-/Betreuer-Chat-ID |
| `STUDENT_CHAT_ID` | Schüler-Chat-ID |

> Frühere Konfigurationen nutzten `CHILD_CHAT_ID`; der neue Name `STUDENT_CHAT_ID` ist in Code und Doku fest verankert.

## Datenstruktur

JSON-Dateien liegen unter `data/user_<chat_id>.json` und enthalten u. a. `chat_id`, `reminder_times` und `week_plan`.

```json
{
  "chat_id": 123456,
  "reminder_times": ["08:00", "18:30"],
  "week_plan": {
    "montag": {"subject": "Mathe", "minutes": 30},
    "dienstag": {"subject": "Englisch", "minutes": 30}
  }
}
```

## Funktionsbeschreibung

- **Anmeldung & Shared State:** Nach `/start` legen sowohl Eltern als auch Schüler einen eigenen `user_<chat_id>.json`-Datensatz an. Sind beide Chat-IDs im `.env` konfiguriert, arbeiten beide Nutzer mit denselben Erinnerungszeiten und Wochenplänen; Änderungen an einem Account werden sofort für den anderen sichtbar.
- **Menüführung:** Der persistente Menü-Button (📋) öffnet eine Reply-Tastatur; Inline-Menüs führen durch `Zeiten verwalten`, `Wochenplan bearbeiten`, `Wochenübersicht` und `Schließen`. Jedes Inline-Keyboard kommuniziert per Callback Queries zurück an `handle_callback` und aktualisiert die Nachricht dynamisch.
- **Reminder-Persistenz:** `reminder_times` werden als Liste (max. 3 Einträge) pro Nutzer gespeichert. Diese Zeiten sind leitend für die `daily_check`-Jobs, die den Tagessatz um 20:00 mit Fragen wie „Warst du heute produktiv?“ versenden und auf Eltern- und Schülerseite dieselbe Erinnerung anzeigen.
- **Wochenplan & Übersicht:** Nutzer können pro Tag (`montag`–`sonntag`) ein Fach, eine Lernzeit und Minuten hinzufügen. Die Wochenübersicht rendert eine tabellarische Darstellung mit farbigen Emojis, Gesamtminuten und ausgeschriebenen Reminder- und Feedback-Zuständen.
- **Jobs & Scheduler:** `apscheduler` kümmert sich um den täglichen `daily_check` (20:00 Uhr UTC+1 Berlin) und eventuelle zusätzliche Test-Reminders. Der Job wird beim Start von `schedule_all_reminders` registriert und durch die JobStore-Instanz von `JobQueue` ausgeführt.
- **Fehlermeldungen & Logging:** Alle Telegram-Antworten und Scheduler-Ereignisse landen in der konsistenten Logging-Konfiguration (`core/logging_config.py`). Exceptions fangen die Handler auf, sodass der Bot selbst bei API-Fehlern (`BadRequest`, abgelaufene Callback-Queries) weiterläuft.

## Tests

```bash
pytest -q
```

## Chat-IDs ermitteln

Sobald Eltern und Schüler jeweils `/start` senden, erscheinen Dateien wie `data/user_193788187.json`. Die IDs daraus in `.env` eintragen und den Bot neu starten.

## Geteilte Funktionalität

Wenn sowohl `PARENT_CHAT_ID` als auch `STUDENT_CHAT_ID` gesetzt sind, teilen sich beide Nutzer:
- **Wochenplan**: Änderungen sind für beide sofort sichtbar.
- **Erinnerungszeiten**: Identische Zeiten werden synchron übernommen.
- **Wochenübersicht**: Betragene Daten zeigen stets den gemeinsamen Lernplan.

## Sicherheitshinweis

`.env` liegt im `.gitignore` und darf nicht veröffentlicht werden. Bei Kompromittierung: BotFather `/revoke` & neuen Token erzeugen.

## Lizenz

MIT
