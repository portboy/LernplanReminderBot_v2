# Lernplan Reminder Bot v2

LernplanReminderBot_v2 ist eine vollständig neugestaltete Version des Lernplan-Reminder-Bots mit einer neuen Nutzerführung, einem klareren Menüfluss und deutlich strukturierteren Erinnerungen für Eltern und Schüler.

## 📚 Dokumentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** – ausführlicher Deployment-Guide (Docker, GHCR, Unraid)
- **[.env.example](.env.example)** – Vorlage für alle erforderlichen Umgebungsvariablen

## Features
Aktuell implementiert:
* **Geteilter Wochenplan** für Eltern und Schüler mit Live-Sync
* **Geteilte Erinnerungszeiten** (bis zu 3 Einträge, synchronisiert zwischen Accounts)
* **Grafische Zeitauswahl** über komfortable Stunden-/Minuten-Picker
* **Übersichtliche Wochenübersicht** mit Emojis, Tabelle und klarer Formatierung
* **Freundliche Texte** statt technischer Fehlermeldungen
* **Permanenter Menü-Button** (📋) für schnellen Zugriff auf alle Funktionen
* **Tägliche 20:00-Abfrage** mit Ja/Nein-Feldern für Lern-Feedback
* **Benachrichtigungen an Eltern** zu Erinnerungen und 20:00-Antworten
* **Zufällige Emojis** in Erinnerungen sowie visuelles Feedback
* **Vollständiges Inline-Menü** zum Bearbeiten von Fächern, Minuten und Zeiten
* **JSON-basierte Nutzerpersistenz** im `data/`-Verzeichnis
* **Scheduling per python-telegram-bot JobQueue** (Europa/Berlin)
* **Docker + GHCR-Images** für Headless-Hosting auf Servern oder Unraid

## Voraussetzungen
- Python 3.11+
- Telegram Bot Token (über @BotFather)
- Optional: Docker und docker-compose (für Containerbetrieb)

## Repository klonen (falls du lokal bauen möchtest)

### Variante A: Git ist installiert
```bash
cd /mnt/user/appdata/builds
git clone https://github.com/portboy/LernplanReminderBot_v2.git
cd LernplanReminderBot_v2
```

### Variante B: ZIP-Download von GitHub
1. Auf GitHub: „Code“ → „Download ZIP“.
2. ZIP nach `/mnt/user/appdata/builds/LernplanReminderBot_v2` entpacken.
3. In das Verzeichnis wechseln: `cd /mnt/user/appdata/builds/LernplanReminderBot_v2`

Danach gelten die unten beschriebenen Build- und Deployment-Schritte.

## Installation (lokal)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env  # Token und Chat IDs eintragen
python -m bot.main
```

## Docker Build & Run (lokal)
```bash
docker build -t lernplan-reminder-bot-v2 .
cp .env.example .env  # Token setzen
# .env konfigurieren

docker run -d --name lernplan-reminder-bot-v2 --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  lernplan-reminder-bot-v2

docker compose up -d --build
```

## Unraid-Deployment (ausführlich)

### Ziel
Der Bot läuft dauerhaft auf deinem Unraid-Server. Einstellungen und Lernpläne bleiben während Updates erhalten.

### Ordnerstruktur (Host)
```
/mnt/user/appdata/LernplanReminderBot_v2/
  ├─ data/              # JSON-Dateien (automatisch)
  └─ .env               # Umgebungsvariablen
```

### 1. AppData-Verzeichnis anlegen
```bash
mkdir -p /mnt/user/appdata/LernplanReminderBot_v2/data
```

### 2. .env anlegen
```bash
nano /mnt/user/appdata/LernplanReminderBot_v2/.env
```
Inhalt:
```env
TELEGRAM_TOKEN=8463xxxxxxxxxxxxxxxxxxxx
LOG_LEVEL=INFO
DATA_DIR=data
PARENT_CHAT_ID=193788187
STUDENT_CHAT_ID=6720705536
```
Hinweise:
- Chat-IDs erst setzen, nachdem beide Nutzer `/start` gesendet haben.
- `LOG_LEVEL=DEBUG` für detailliertes Logging.

### 3. Option A: Vorgefertigtes GHCR-Image verwenden (empfohlen)
```bash
docker run -d \
  --name lernplan-reminder-bot-v2 \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot_v2/.env \
  -v /mnt/user/appdata/LernplanReminderBot_v2/data:/app/data \
  ghcr.io/portboy/lernplan-reminder-bot-v2:latest
```

### 4. Option B: Eigenes Image lokal bauen
```bash
cd /mnt/user/appdata/builds/LernplanReminderBot_v2
docker build -t lernplan-reminder-bot-v2:latest .
docker run -d \
  --name lernplan-reminder-bot-v2 \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot_v2/.env \
  -v /mnt/user/appdata/LernplanReminderBot_v2/data:/app/data \
  lernplan-reminder-bot-v2:latest
```

### 5. docker-compose (lokaler Build)
`/mnt/user/appdata/LernplanReminderBot_v2/docker-compose.yml`:
```yaml
version: "3.9"
services:
  lernplan-reminder-bot-v2:
    image: lernplan-reminder-bot-v2:latest
    build: /mnt/user/appdata/builds/LernplanReminderBot_v2
    restart: unless-stopped
    env_file: /mnt/user/appdata/LernplanReminderBot_v2/.env
    volumes:
      - /mnt/user/appdata/LernplanReminderBot_v2/data:/app/data
```
Starten:
```bash
docker compose -f /mnt/user/appdata/LernplanReminderBot_v2/docker-compose.yml up -d --build
```

### 6. Unraid GUI (Template manuell)
1. Docker Tab → „Add Container“ → „Advanced View“.
2. Repository: `ghcr.io/portboy/lernplan-reminder-bot-v2:latest` oder `lernplan-reminder-bot-v2:latest` (lokal).
3. Add Path: Host `/mnt/user/appdata/LernplanReminderBot_v2/data` → Container `/app/data`.
4. Add Variable: `TELEGRAM_TOKEN` (Pflicht).
5. Add Variable: `PARENT_CHAT_ID`, `STUDENT_CHAT_ID`, optional `LOG_LEVEL`.
6. Keine Ports erforderlich.
7. Apply.

### 7. Testen
1. Beide Accounts (Eltern & Schüler) `/start` senden.
2. `/menu` ausprobieren.
3. Zeit eintragen (Button → z. B. `08:00`).
4. `/test` senden → Erinnerung wird ausgelöst.

### 8. Logs prüfen
```bash
docker logs -f lernplan-reminder-bot-v2
```

### 9. Updates
#### Variante Registry (empfohlen)
```bash
docker pull ghcr.io/portboy/lernplan-reminder-bot-v2:latest
docker stop lernplan-reminder-bot-v2
docker rm lernplan-reminder-bot-v2
docker run -d \
  --name lernplan-reminder-bot-v2 \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot_v2/.env \
  -v /mnt/user/appdata/LernplanReminderBot_v2/data:/app/data \
  ghcr.io/portboy/lernplan-reminder-bot-v2:latest
```
#### Variante lokaler Build
```bash
docker stop lernplan-reminder-bot-v2
docker rm lernplan-reminder-bot-v2
# Repo aktualisieren
docker build -t lernplan-reminder-bot-v2:latest .
docker run -d \
  --name lernplan-reminder-bot-v2 \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot_v2/.env \
  -v /mnt/user/appdata/LernplanReminderBot_v2/data:/app/data \
  lernplan-reminder-bot-v2:latest
```

### 10. Backup
```bash
tar czf lernplan-bot-backup.tgz -C /mnt/user/appdata LernplanReminderBot_v2
```

### 11. Häufige Probleme
| Symptom | Ursache | Lösung |
|---------|---------|--------|
| Keine Bot-Antwort | Token fehlt/fehlerhaft | Token kontrollieren, Logs prüfen |
| 20:00-Frage fehlt | `STUDENT_CHAT_ID` fehlt oder Container nach 20:00 gestartet | ID setzen & bis morgen warten |
| Keine Eltern-Info | `PARENT_CHAT_ID` fehlt | ID ergänzen (Container neu starten) |
| Erinnerungen fehlen | Zeit noch nicht erreicht / Jobs nicht geplant | `/menu` → Zeit neu speichern |
| JSON-Datei fehlt | Chat hat nie `/start` gesendet | `/start` von beiden anstoßen |

### 12. Sicherheit
Token niemals öffentlich teilen. Bei Verdacht: BotFather `/revoke` & neuen Token setzen.

### 13. Entfernen
```bash
docker stop lernplan-reminder-bot-v2
docker rm lernplan-reminder-bot-v2
rm -rf /mnt/user/appdata/LernplanReminderBot_v2
```

### 14. Optionale Erweiterungen
- Watchtower für automatische Updates
- Separates Logging-Verzeichnis (`/app/logs`)
- Healthchecks über eigenes Skript

## .env Variablen
| Variable | Bedeutung |
|----------|-----------|
| `TELEGRAM_TOKEN` | Telegram Bot-Token |
| `LOG_LEVEL` | z. B. INFO / DEBUG |
| `DATA_DIR` | Pfad für JSON-Daten (Default: data) |
| `PARENT_CHAT_ID` | Eltern-/Betreuer-Chat-ID |
| `STUDENT_CHAT_ID` | Schüler-Chat-ID |

Migration: Alte Konfigurationen nutzen `CHILD_CHAT_ID`. Diese muss auf `STUDENT_CHAT_ID` umbenannt werden (gleiche ID).

## Datenstruktur
`data/user_<chat_id>.json`
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

## Tests
```bash
pytest -q
```

## Chat IDs ermitteln
Beide Nutzer (Eltern & Schüler) senden am besten einmal `/start`. Danach stehen die Chat-IDs als Dateinamen in `data/` (z. B. `user_123456.json`). Diese Werte in `.env` als `PARENT_CHAT_ID` und `STUDENT_CHAT_ID` eintragen und Container einmal neu starten.

## Geteilte Funktionalität
Wenn sowohl `PARENT_CHAT_ID` als auch `STUDENT_CHAT_ID` gesetzt sind, teilen sich beide Nutzer:
* **Wochenplan** – Änderungen laden für beide Nutzer sofort nach
* **Erinnerungszeiten** – identische Zeiten für beide Accounts
* **Wochenübersicht** – zeigt stets den aktuellen Stand des gemeinsamen Lernplans

Dadurch lässt sich der Lernplan zusammen verwalten.

## Lizenz
MIT

## Sicherheitshinweis
Nutze `.env` für Tokens. Die Datei ist im Repository über `.gitignore` ausgeschlossen. Sollte der Token kompromittiert sein: BotFather `/revoke` & neuen Token einrichten.

Hinweis: `CHILD_CHAT_ID` wurde in `STUDENT_CHAT_ID` umbenannt; Code & Doku sind angepasst.
