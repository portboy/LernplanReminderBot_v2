# Deployment Guide

## 🐳 Docker Deployment Optionen

### Option 1: Lokale Entwicklung (mit Build)

```bash
# Konfiguration erstellen
mkdir -p userconfig
nano userconfig/bot_config.json
```

**`userconfig/bot_config.json`:**

```json
{
  "telegram_token": "DEIN_BOT_TOKEN",
  "student_chat_id": 123456789,
  "parent_chat_id": 987654321,
  "timezone": "Europe/Berlin",
  "log_level": "INFO",
  "allowed_subjects": [
    { "name": "Mathe", "emoji": "🔢" },
    { "name": "Englisch", "emoji": "🇬🇧" }
  ]
}
```

```bash
# Container bauen und starten
docker compose up -d

# Logs verfolgen
docker compose logs -f

# Container stoppen
docker compose down
```

### Option 2: Produktion über docker-compose.prod.yml

```bash
# Konfiguration anlegen (siehe oben)
mkdir -p userconfig data
nano userconfig/bot_config.json

docker compose -f docker-compose.prod.yml up -d
```

Updates:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Option 3: Unraid Server (empfohlen)

**Setup-Schritte:**

1. **Verzeichnisse erstellen**
   ```bash
   mkdir -p /mnt/user/appdata/LernplanReminderBot_v2/data
   mkdir -p /mnt/user/appdata/LernplanReminderBot_v2/userconfig
   ```

2. **Konfiguration anlegen**
   ```bash
   nano /mnt/user/appdata/LernplanReminderBot_v2/userconfig/bot_config.json
   ```
   Inhalt: Siehe `bot_config.json` Beispiel oben.

3. **docker-compose.yml erstellen**
   ```bash
   nano /mnt/user/appdata/LernplanReminderBot_v2/docker-compose.yml
   ```
   Inhalt:
   ```yaml
   services:
     lernplan-reminder-bot-v2:
       image: ghcr.io/portboy/lernplan-reminder-bot-v2:latest
       container_name: lernplan-reminder-bot-v2
       restart: unless-stopped
       environment:
         - TZ=Europe/Berlin
       volumes:
         - ./data:/app/data
         - ./userconfig:/app/userconfig
         - /etc/localtime:/etc/localtime:ro
         - /etc/timezone:/etc/timezone:ro
       healthcheck:
         test: ["CMD", "python", "src/healthcheck.py"]
         interval: 60s
         timeout: 10s
         retries: 3
         start_period: 15s
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

4. **Container starten**
   ```bash
   cd /mnt/user/appdata/LernplanReminderBot_v2
   docker compose up -d
   ```

5. **Logs prüfen**
   ```bash
   docker logs -f lernplan-reminder-bot-v2
   ```

### Option 4: GHCR Image manuell verwenden

```bash
docker pull ghcr.io/portboy/lernplan-reminder-bot-v2:latest
docker run -d \
   --name lernplan-reminder-bot-v2 \
   --restart unless-stopped \
   -e TZ=Europe/Berlin \
   -v $(pwd)/data:/app/data \
   -v $(pwd)/userconfig:/app/userconfig \
   ghcr.io/portboy/lernplan-reminder-bot-v2:latest
```

## ⚙️ Konfiguration

### JSON-Datei (Empfohlen)

Die primäre Konfiguration erfolgt über `userconfig/bot_config.json`. Diese Datei wird im Container unter `/app/userconfig/bot_config.json` gemountet.

Alle verfügbaren Felder sind in der [README.md](README.md#2-konfigurationsreferenz-bot_configjson) dokumentiert.

### Umgebungsvariablen (Override)

Einzelne Werte aus der JSON-Datei können per Umgebungsvariable überschrieben werden:

| Env-Variable | JSON-Feld | Beispiel |
| :--- | :--- | :--- |
| `TELEGRAM_TOKEN` | `telegram_token` | `123:ABC` |
| `STUDENT_CHAT_ID` | `student_chat_id` | `123456789` |
| `PARENT_CHAT_ID` | `parent_chat_id` | `987654321` |
| `TIMEZONE` | `timezone` | `Europe/Berlin` |
| `LOG_LEVEL` | `log_level` | `DEBUG` |
| `DATA_DIR` | `data_dir` | `/app/data` |

Priorität: Umgebungsvariable > JSON-Datei > Default-Wert.

## 🏥 Health Check

Der Container enthält einen echten Health Check (`src/healthcheck.py`), der folgendes prüft:

1. **Konfiguration ladbar** — `bot_config.json` kann geparst werden
2. **Data-Verzeichnis schreibbar** — Testdatei in `/app/data` erstellen/löschen
3. **Telegram-API erreichbar** — HTTP HEAD an `api.telegram.org` (5s Timeout)

Status prüfen:

```bash
docker inspect --format='{{.State.Health.Status}}' lernplan-reminder-bot-v2
```

## 🔄 Updates

### Automatisch (Watchtower empfohlen)

```bash
docker run -d \
   --name watchtower \
   --restart unless-stopped \
   -v /var/run/docker.sock:/var/run/docker.sock \
   containrrr/watchtower \
   --cleanup \
   --interval 3600 \
   lernplan-reminder-bot-v2
```

### Manuell

```bash
docker compose pull
docker compose up -d
docker image prune -f
```

### Auf Unraid

```bash
cd /mnt/user/appdata/LernplanReminderBot_v2
docker compose pull
docker compose up -d
```

## 📊 Monitoring

```bash
# Aktuelle Logs
docker logs lernplan-reminder-bot-v2

# Live-Logs
docker logs -f lernplan-reminder-bot-v2

# Letzte 100 Zeilen
docker logs --tail 100 lernplan-reminder-bot-v2

# Health Check Status
docker inspect --format='{{json .State.Health}}' lernplan-reminder-bot-v2 | python -m json.tool
```

## 🐛 Troubleshooting

**Bot startet nicht**

```bash
docker logs lernplan-reminder-bot-v2
# Prüfe: Fehlermeldung zu telegram_token oder student_chat_id
```

**Health Check schlägt fehl**

```bash
# Manuell im Container ausführen:
docker exec lernplan-reminder-bot-v2 python src/healthcheck.py
```

**Daten werden nicht gespeichert**

```bash
docker inspect lernplan-reminder-bot-v2 | grep -A 5 "Mounts"
ls -la ./data/
```

**Konfiguration wird nicht geladen**

```bash
# Prüfe ob die Datei korrekt gemountet ist:
docker exec lernplan-reminder-bot-v2 cat /app/userconfig/bot_config.json
```

**Schneller Neustart**

```bash
docker compose restart lernplan-reminder-bot-v2
# oder mit neuem Build:
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 🔒 Sicherheit

1. **Tokens niemals öffentlich committen** — `bot_config.json` sollte in `.gitignore` stehen
2. **Non-Root-User** — Container läuft als `botuser` (UID 1000)
3. **Nur notwendige Volumes mounten** — `data/` und `userconfig/`
4. **Ressourcenlimits** setzen (siehe `docker-compose.prod.yml`)
5. **Regelmäßige Updates** durchführen

### Backup

```bash
tar -czf backup-$(date +%Y%m%d).tar.gz data/ userconfig/
```

### Restore

```bash
tar -xzf backup-YYYYMMDD.tar.gz
docker compose restart
```
