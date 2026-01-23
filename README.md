# Lernplan Reminder Bot

Telegram Bot zur täglichen Erinnerung an einen Lernplan (z.B. Mathe / Englisch) für einen Schüler bzw. eine Schülerin – mit Erinnerungen, Tagesplan und täglicher Bestätigungs-Abfrage für Eltern/Betreuer.

## 📚 Dokumentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Ausführliche Deployment-Anleitung für Docker, Unraid, etc.
- **[.env.example](.env.example)** - Beispiel-Konfiguration

## Features
Aktuell implementiert:
* **Geteilter Wochenplan**: Beide Nutzer (Eltern/Schüler) teilen denselben Plan und können ihn bearbeiten
* **Geteilte Erinnerungszeiten**: Bis zu 3 tägliche Zeiten, synchronisiert zwischen beiden Nutzern
* **Grafische Zeitauswahl**: Benutzerfreundliche Stunden/Minuten-Picker statt Texteingabe
* **Schöne Wochenübersicht**: Visuell ansprechend mit Emojis, Tabelle und besserer Formatierung
* **Lustige Fehlermeldungen**: Amüsante statt technische Fehlermeldungen für bessere Benutzererfahrung
* **Menü-Button**: Permanenter "📋 Menü" Button für einfachen Zugang zu allen Funktionen
* 20:00 Uhr Abfrage an den Schüler: "Hast du heute gelernt?" mit Ja/Nein Buttons
* Benachrichtigung an Eltern/Betreuer über gesendete Erinnerungen & Antwort der 20-Uhr-Frage
* Zufällige Emojis in Erinnerungen
* Positives (Pferde-Bilder) / negatives (traurige GIFs) Feedback
* Commands: `/start`, `/help`, `/plan`, `/zeiten`, `/addzeit`, `/delzeit`, `/heute`, `/test`, `/menu`
* Vollständiges Inline-Menü zur Bearbeitung von Zeiten und Wochenplan (Fach & Minuten)
* JSON-Speicherung je Chat unter `data/`
* Scheduling per python-telegram-bot JobQueue (Daily Jobs, Timezone Europe/Berlin)
* Docker & docker-compose + vorgebaute Container Images (GHCR)

Geplant / Ideen:
* Zusätzliche optionale Fächer (aktuell Mathe, Englisch – Architektur erlaubt Erweiterung)
* Mehr Testabdeckung (Callback- & Scheduling-Logik)
* Optionale Healthcheck- und Watchtower-Beispiele
* Erweiterte Statistiken und Lernfortschritt-Tracking

## Voraussetzungen
- Python 3.11+
- Telegram Bot Token (von @BotFather)

### Repository klonen (falls du lokal bauen willst)
Variante A: Git ist installiert:
```bash
cd /mnt/user/appdata/builds
git clone https://github.com/portboy/LernplanReminderBot.git
cd LernplanReminderBot
```

Variante B: ZIP Download:
1. Auf GitHub: "Code" → "Download ZIP".
2. ZIP entpacken nach `/mnt/user/appdata/builds/LernplanReminderBot`.
3. Wechsel in dieses Verzeichnis.

Dann kannst du wie unten beschrieben bauen.

<!-- GHCR Direktnutzung ist jetzt weiter unten in Abschnitt A strukturiert -->

## Installation (Lokal)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env  # Token eintragen
python -m bot.main
```

## Docker Build & Run
```bash
docker build -t lernplan-bot .
cp .env.example .env  # Token setzen
# .env bearbeiten

docker run -d --name lernplan-bot --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/data:/app/data lernplan-bot
```

```bash
docker compose up -d --build
```

## Unraid Deployment (ausführlich)

### Ziel
Der Bot läuft dauerhaft auf deinem Unraid Server. Einstellungen & Plan bleiben nach Updates erhalten.

### Verzeichnisstruktur (Host)
```
/mnt/user/appdata/LernplanReminderBot/
  ├─ data/              # JSON Dateien (automatisch erzeugt)
  └─ .env               # Environment Variablen
```

### 1. AppData Ordner anlegen
```bash
mkdir -p /mnt/user/appdata/LernplanReminderBot/data
```

```
TELEGRAM_TOKEN=8463xxxxxxxxxxxxxxxxxxxx
LOG_LEVEL=INFO
DATA_DIR=data
PARENT_CHAT_ID=193788187
STUDENT_CHAT_ID=6720705536
```
Hinweise:
- Chat IDs erst setzen, nachdem beide (Eltern & Schüler) einmal `/start` geschickt haben.
- `LOG_LEVEL=DEBUG` für Diagnose.

### 3. (Option A) Vorgefertigtes Image starten (empfohlen)
```bash
docker run -d \
  --name lernplan-reminder-bot \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot/.env \
  -v /mnt/user/appdata/LernplanReminderBot/data:/app/data \
  ghcr.io/portboy/lernplan-reminder-bot:latest
```

### 4. (Option B) Image lokal bauen & starten
Falls Repo lokal geklont unter z.B. `/mnt/user/appdata/builds/LernplanReminderBot`:
```bash
cd /mnt/user/appdata/builds/LernplanReminderBot
docker build -t lernplan-reminder-bot:latest .
docker run -d \
  --name lernplan-reminder-bot \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot/.env \
  -v /mnt/user/appdata/LernplanReminderBot/data:/app/data \
  lernplan-reminder-bot:latest
```

### 5. docker compose (lokaler Build)
Datei `/mnt/user/appdata/LernplanReminderBot/docker-compose.yml`:
```yaml
version: "3.9"
services:
  lernplan-bot:
    image: lernplan-reminder-bot:latest
    build: /mnt/user/appdata/builds/LernplanReminderBot
    restart: unless-stopped
    env_file: /mnt/user/appdata/LernplanReminderBot/.env
    volumes:
      - /mnt/user/appdata/LernplanReminderBot/data:/app/data
```
Starten:
```bash
docker compose -f /mnt/user/appdata/LernplanReminderBot/docker-compose.yml up -d --build
```

### 6. Unraid GUI (Template manuell)
1. Docker Tab → "Add Container" → Advanced View.
2. Repository: `ghcr.io/portboy/lernplan-reminder-bot:latest` (oder lokaler Build-Name).
3. Add Path: Host=`/mnt/user/appdata/LernplanReminderBot/data` → Container=`/app/data`.
4. Add Variable: `TELEGRAM_TOKEN` (Pflicht).
5. Add Variable: `PARENT_CHAT_ID`, `STUDENT_CHAT_ID`, optional `LOG_LEVEL`.
6. Keine Ports nötig.
7. Apply.

### 7. Test
1. In Telegram `/start` von beiden Accounts.
2. `/menu` ausprobieren.
3. Zeit hinzufügen (Button ➜ Eingabe `08:00`).
4. `/test` senden → Test-Erinnerung sollte erscheinen.

### 8. Logs prüfen
```bash
docker logs -f lernplan-reminder-bot
```

### 9. Update-Prozess
Variante Registry (empfohlen):
```bash
docker pull ghcr.io/portboy/lernplan-reminder-bot:latest
docker stop lernplan-reminder-bot
docker rm lernplan-reminder-bot
docker run -d \
  --name lernplan-reminder-bot \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot/.env \
  -v /mnt/user/appdata/LernplanReminderBot/data:/app/data \
  ghcr.io/portboy/lernplan-reminder-bot:latest
```

Variante lokaler Build:
```bash
docker stop lernplan-reminder-bot
docker rm lernplan-reminder-bot
# (Repo aktualisieren: git pull oder neue Version kopieren)
docker build -t lernplan-reminder-bot:latest .
docker run -d --name lernplan-reminder-bot \
  --restart unless-stopped \
  --env-file /mnt/user/appdata/LernplanReminderBot/.env \
  -v /mnt/user/appdata/LernplanReminderBot/data:/app/data \
  lernplan-reminder-bot:latest
```
Persistente Daten bleiben erhalten.

### 10. Backup (empfohlen)
```bash
tar czf lernplan-bot-backup.tgz -C /mnt/user/appdata LernplanReminderBot
```
Wiederherstellung: Archiv entpacken, Container neu starten.

### 11. Häufige Probleme
| Symptom | Ursache | Lösung |
|---------|---------|--------|
| Keine Bot-Antwort | Falscher Token | Token prüfen / Logs ansehen |
| 20-Uhr Frage fehlt | `STUDENT_CHAT_ID` fehlt / Container nach 20:00 gestartet | ID setzen & bis morgen warten |
| Keine Eltern-Info | `PARENT_CHAT_ID` nicht gesetzt | In `.env` ergänzen |
| Keine Erinnerungen | Zeit noch nicht erreicht / Job nicht neu geplant | Warten oder Zeit neu speichern (/menu) |
| JSON fehlt | Chat hat nie `/start` gesendet | `/start` senden |

### 12. Sicherheit
Token privat halten. Bei Verdacht → BotFather `/revoke` und neuen Token setzen.

### 13. Entfernen
```bash
docker stop lernplan-reminder-bot
docker rm lernplan-reminder-bot
# Optional Daten löschen:
rm -rf /mnt/user/appdata/LernplanReminderBot
```

### 14. Optionale Erweiterungen
- Watchtower für Auto-Updates.
- Separates Logging-Verzeichnis (`/app/logs`).
- Healthcheck Skript (kann später ergänzt werden).

## .env Variablen
| Variable | Bedeutung |
|----------|-----------|
| `TELEGRAM_TOKEN` | Bot API Token |
| `LOG_LEVEL` | z.B. INFO / DEBUG |
| `DATA_DIR` | Pfad für JSON Daten (Default: data) |
| `PARENT_CHAT_ID` | Chat ID des Elternteils / Betreuers für Info-Benachrichtigungen |
| `STUDENT_CHAT_ID` | Chat ID des Schülers für 20-Uhr-Abfrage |

Migration: Falls du eine ältere Version genutzt hast, ersetze in deiner `.env` den alten Namen `CHILD_CHAT_ID` durch `STUDENT_CHAT_ID` (Inhalt = gleiche ID). Alte Container können sonst die Schüler-ID nicht mehr finden.

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
Einfachster Weg: Beide Nutzer (Eltern & Schüler) senden einmal `/start` an den Bot. Danach findest du die Chat IDs in den erzeugten Dateien unter `data/` (Dateiname `user_<chatid>.json`). Diese Werte in `.env` als `PARENT_CHAT_ID` und `STUDENT_CHAT_ID` eintragen und Container neu starten.

## Geteilte Funktionalität
Wenn sowohl `PARENT_CHAT_ID` als auch `STUDENT_CHAT_ID` konfiguriert sind, teilen sich beide Nutzer:
* **Wochenplan**: Änderungen von einem Nutzer werden sofort auch beim anderen sichtbar
* **Erinnerungszeiten**: Alle Zeiten werden zwischen beiden Accounts synchronisiert
* **Wochenübersicht**: Zeigt immer den aktuellen geteilten Stand an

Dies ermöglicht es beiden Nutzern, gemeinsam den Lernplan zu verwalten und zu bearbeiten.

## Lizenz
MIT

## Sicherheitshinweis
Gib den echten Token niemals öffentlich weiter. Verwende `.env` (diese Datei wird durch `.gitignore` ausgeschlossen). Falls Token kompromittiert: Beim BotFather regenerieren.

---
Hinweis: Variable `CHILD_CHAT_ID` wurde in `STUDENT_CHAT_ID` umbenannt (neutralere Bezeichnung). Code & Doku sind bereits angepasst.
