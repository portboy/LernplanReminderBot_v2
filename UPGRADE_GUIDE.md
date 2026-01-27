# Upgrade Guide - LernplanReminderBot v2 Refactored

## 🎉 Was wurde verbessert?

### ✅ Sofort (Critical) - Behoben:
1. **Timezone-Type vereinheitlicht**: Konsistente Verwendung von `ZoneInfo`
2. **Race Condition behoben**: Scheduler löscht nur noch dynamische Jobs, nicht System-Jobs
3. **Doppelte ALLOWED_SUBJECTS entfernt**: Zentrale Config-Verwaltung
4. **Token-Validation beim Start**: Frühe Fehlerkennung mit klarer Meldung

### ✅ Kurzfristig (High Priority) - Implementiert:
5. **Pydantic Validation**: Alle Eingaben werden validiert (Chat-IDs, Zeiten, Minuten)
6. **Dateinamen anonymisiert**: SHA256-Hash statt Chat-ID in Dateinamen + Mapping-File
7. **Error-Handler**: Globaler Error-Handler mit User-Benachrichtigung
8. **Docker Multi-Stage Build**: Kleineres Image, keine Dev-Dependencies in Production

### ✅ Mittelfristig - Implementiert:
9. **Service-Layer**: Trennung von Business-Logik (`LernplanService`)
10. **UI-Module**: Separate Keyboard-Builder und Message-Builder
11. **Structured Logging**: Konsistentes Logging-Format
12. **Erweiterte Fächerverwaltung**: Dynamische Fächer via JSON-Config

### 🆕 Zusätzliche Features:
- **JSON-basierte Konfiguration**: Komplette Config über `userconfig/bot_config.json`
- **Hot-Reload Config**: Nur Container-Neustart nötig, kein Re-Deploy
- **Emoji & Farben pro Fach**: Individualisierbare Fächer
- **Nicht-Root User im Container**: Security Best Practice
- **Health Checks**: Docker Healthcheck implementiert

---

## 📂 Neue Dateistruktur

```
src/
├── bot/
│   ├── main.py           # Alt (deprecated)
│   └── main_new.py       # Neu (refactored)
├── core/
│   ├── __init__.py
│   ├── config.py         # NEU: Config-Management mit Pydantic
│   └── logging_config.py # Erweitert
├── models/
│   ├── __init__.py
│   └── settings.py       # Erweitert mit Pydantic & Anonymisierung
├── services/
│   └── __init__.py       # NEU: LernplanService
└── ui/
    ├── __init__.py
    ├── keyboards.py      # NEU: Keyboard-Builder
    └── messages.py       # NEU: Message-Builder

userconfig/
└── bot_config.json       # NEU: Zentrale Konfiguration

data/
├── user_<hash>.json      # Anonymisiert (statt user_<chat_id>.json)
└── id_mapping.json       # NEU: Chat-ID Recovery Mapping
```

---

## 🚀 Migration von v1 zu v2

### Schritt 1: Konfiguration erstellen

Erstelle `userconfig/bot_config.json`:

```json
{
  "telegram_token": "YOUR_BOT_TOKEN_HERE",
  "student_chat_id": 123456789,
  "parent_chat_id": 987654321,
  "timezone": "Europe/Berlin",
  "log_level": "INFO",
  "allowed_subjects": [
    {
      "name": "Mathe",
      "emoji": "🔢",
      "color": "#FF6B6B"
    },
    {
      "name": "Englisch",
      "emoji": "🇬🇧",
      "color": "#4ECDC4"
    },
    {
      "name": "Deutsch",
      "emoji": "📝",
      "color": "#95E1D3"
    }
  ],
  "morning_prompt_time": "07:30",
  "daily_check_time": "20:00",
  "jokers_per_week": 1
}
```

**Wichtig**: Die Konfiguration wird beim Start gelesen. Änderungen werden erst nach Container-Neustart aktiv.

### Schritt 2: Environment-Variablen (Optional)

Du kannst auch weiterhin `.env` verwenden. Environment-Variablen überschreiben JSON-Config:

```bash
TELEGRAM_TOKEN=your_token
STUDENT_CHAT_ID=123456789
PARENT_CHAT_ID=987654321
TIMEZONE=Europe/Berlin
LOG_LEVEL=DEBUG
```

### Schritt 3: Container starten

**Image-Tags:** Für jeden Branch wird automatisch ein Image gebaut:
- `:latest` / `:main` → Stable Production Release
- `:develop` → Testing Branch mit neuesten Features
- `:<branch-name>` → Spezifischer Feature-Branch

```bash
# Option 1: Lokaler Build
docker-compose down
docker-compose build
docker-compose up -d

# Option 2: GHCR Image (empfohlen)
# Standard (main/latest):
docker compose -f docker-compose.ghcr.yml up -d

# Oder develop Branch:
# Editiere docker-compose.ghcr.yml, ändere :latest zu :develop
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

### Schritt 4: Migration alter Daten

Alte `data/user_<chat_id>.json` Dateien werden automatisch migriert:
- Beim ersten Zugriff wird die Datei umbenannt
- Ein `id_mapping.json` wird erstellt für Recovery

---

## 🔧 Konfiguration ändern (ohne Neudeployment)

### Fächer hinzufügen/ändern

Editiere `userconfig/bot_config.json`:

```json
{
  "allowed_subjects": [
    {
      "name": "Physik",
      "emoji": "⚛️",
      "color": "#F38181"
    },
    {
      "name": "Geschichte",
      "emoji": "📜",
      "color": "#AA96DA"
    }
  ]
}
```

**Neustart**:
```bash
docker-compose restart
```

### Zeiten anpassen

```json
{
  "morning_prompt_time": "08:00",
  "daily_check_time": "21:00",
  "dynamic_planning_times": ["08:00", "10:00", "15:00", "19:00"]
}
```

**Neustart**:
```bash
docker-compose restart
```

### Bilder/GIFs ändern

```json
{
  "horse_happy_images": [
    "https://your-image-url.com/happy1.jpg",
    "https://your-image-url.com/happy2.jpg"
  ],
  "sad_gifs": [
    "https://your-gif-url.com/sad1.gif"
  ]
}
```

---

## 🐳 Docker-Befehle

### Lokales Development

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Logs anschauen
docker-compose logs -f

# Status prüfen
docker-compose ps

# Stoppen
docker-compose down
```

### Production (Unraid/Server)

```bash
docker run -d \
  --name lernplan-reminder-bot-v2 \
  --restart unless-stopped \
  -v /path/to/data:/app/data \
  -v /path/to/userconfig:/app/userconfig \
  your-registry/lernplan-reminder-bot-v2:latest
```

---

## 📊 Monitoring & Debugging

### Logs Level ändern

In `userconfig/bot_config.json`:
```json
{
  "log_level": "DEBUG"
}
```

Neustart, dann:
```bash
docker-compose logs -f
```

### Gesundheitsprüfung

```bash
docker inspect lernplan-reminder-bot-v2 | grep -A 10 Health
```

### Test-Commands

```bash
/testdaily  # Daily Check manuell triggern
/test       # Heutigen Reminder anzeigen
```

---

## 🔒 Sicherheit & Datenschutz

### Anonymisierte Dateinamen

- Alt: `data/user_193788187.json` (Chat-ID sichtbar)
- Neu: `data/user_a3f5e9d1b2c4f8e6.json` (SHA256-Hash)
- Recovery via: `data/id_mapping.json` (sollte backup'ed werden)

### Non-Root Container

Der Container läuft als User `botuser` (UID 1000), nicht als root.

### Secrets Management

**Best Practice**: Nutze Docker Secrets statt `.env` in Production:

```yaml
services:
  bot:
    secrets:
      - telegram_token
    environment:
      TELEGRAM_TOKEN_FILE: /run/secrets/telegram_token

secrets:
  telegram_token:
    file: ./secrets/telegram_token.txt
```

---

## 🧪 Testing

### Unit Tests

```bash
# In virtualenv
pip install -e .[dev]
pytest tests/ -v

# Coverage
pytest --cov=src tests/
```

### Integration Test

```bash
# Start Bot im Test-Mode
LOG_LEVEL=DEBUG python -m bot.main_new
```

---

## 🆘 Troubleshooting

### "Configuration validation failed"

➡️ Prüfe `userconfig/bot_config.json` auf Syntaxfehler:
```bash
python -c "import json; json.load(open('userconfig/bot_config.json'))"
```

### "TELEGRAM_TOKEN not set or invalid"

➡️ Token in `bot_config.json` oder `.env` setzen

### Container startet nicht

```bash
# Logs prüfen
docker-compose logs

# Manuell starten für Debug
docker run -it --rm \
  -v $(pwd)/userconfig:/app/userconfig \
  -v $(pwd)/data:/app/data \
  lernplan-reminder-bot-v2 \
  python -m bot.main_new
```

### Alte Daten nicht migriert

```bash
# Manuell prüfen
ls -la data/

# Mapping prüfen
cat data/id_mapping.json
```

---

## 📈 Performance

### Ressourcen-Limits setzen

In `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 256M
    reservations:
      memory: 128M
```

### Image-Größe

- Alt (Single-Stage): ~450MB
- Neu (Multi-Stage): ~180MB

---

## 🔄 Backup & Recovery

### Was soll backup'ed werden?

```bash
# Kritisch
data/id_mapping.json        # Chat-ID Mapping
userconfig/bot_config.json  # Config

# User-Daten
data/user_*.json
```

### Backup-Script

```bash
#!/bin/bash
tar -czf backup_$(date +%Y%m%d).tar.gz \
  data/ \
  userconfig/bot_config.json
```

---

## 📝 Changelog

### v2.0.0 (Refactored)

**Breaking Changes:**
- Dateinamen geändert (automatische Migration)
- `bot.main` → `bot.main_new` (alter Code bleibt als Referenz)

**New Features:**
- JSON-basierte Konfiguration
- Erweiterte Fächerverwaltung
- Service-Layer Architektur
- Multi-Stage Docker Build
- Pydantic Validation

**Fixes:**
- Timezone-Handling
- Race Condition in Scheduler
- Token-Validation
- Error-Handling

**Security:**
- Anonymisierte Dateinamen
- Non-Root Container
- Input-Validation

---

## 🤝 Contributing

### Code-Style

```bash
# Ruff für Linting
ruff check src/

# Format
ruff format src/
```

### Tests hinzufügen

Siehe `tests/` für Beispiele.

---

## 📞 Support

Bei Problemen:
1. Logs prüfen: `docker-compose logs -f`
2. Config validieren: siehe Troubleshooting
3. Issue auf GitHub erstellen mit:
   - Log-Output
   - Config (ohne Token!)
   - Docker-Version
