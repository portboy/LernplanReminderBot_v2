# Deployment Guide

## 📋 Wichtige Hinweise

- **[GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)** - Falls du Build-Fehler mit GitHub Actions hast (Permission denied beim Push zu GHCR)

## 🐳 Docker Deployment Optionen

### Option 1: Lokale Entwicklung (mit Build)

```bash
# .env Datei erstellen (siehe .env.example)
cp .env.example .env
# .env bearbeiten und Werte eintragen

# Container starten
docker compose up -d

# Logs ansehen
docker compose logs -f

# Container stoppen
docker compose down
```

### Option 2: Produktion mit vorgefertigtem Image

```bash
# .env Datei erstellen
cp .env.example .env
# .env bearbeiten und Werte eintragen

# Container mit vorgefertigtem Image starten
docker compose -f docker-compose.prod.yml up -d

# Update auf neueste Version
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Logs ansehen
docker compose -f docker-compose.prod.yml logs -f
```

### Option 3: Unraid Server

**Pfade auf Unraid:**
- Config: `/mnt/user/appdata/LernplanReminderBot/.env`
- Daten: `/mnt/user/appdata/LernplanReminderBot/data`

**Setup-Schritte:**

1. **Verzeichnisse erstellen:**
   ```bash
   mkdir -p /mnt/user/appdata/LernplanReminderBot/data
   ```

2. **.env Datei erstellen:**
   ```bash
   nano /mnt/user/appdata/LernplanReminderBot/.env
   ```
   
   Inhalt:
   ```env
   TELEGRAM_TOKEN=your_bot_token_here
   STUDENT_CHAT_ID=your_student_chat_id
   PARENT_CHAT_ID=your_parent_chat_id
   DATA_DIR=data
   LOG_LEVEL=INFO
   ```

3. **docker-compose.yml erstellen:**
   ```bash
   nano /mnt/user/appdata/LernplanReminderBot/docker-compose.yml
   ```
   
   Inhalt:
   ```yaml
   version: "3.9"
   services:
     lernplan-bot:
       image: ghcr.io/portboy/lernplan-reminder-bot:latest
       container_name: lernplan-reminder-bot
       restart: unless-stopped
       env_file: /mnt/user/appdata/LernplanReminderBot/.env
       volumes:
         - /mnt/user/appdata/LernplanReminderBot/data:/app/data
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

4. **Container starten:**
   ```bash
   cd /mnt/user/appdata/LernplanReminderBot
   docker compose up -d
   ```

5. **Logs prüfen:**
   ```bash
   docker logs -f lernplan-reminder-bot
   ```

### Option 4: GitHub Container Registry (GHCR) manuell

```bash
# Image pullen
docker pull ghcr.io/portboy/lernplan-reminder-bot:latest

# Container starten
docker run -d \
  --name lernplan-reminder-bot \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  ghcr.io/portboy/lernplan-reminder-bot:latest
```

---

## 🔄 Updates

### Automatisch mit Watchtower (empfohlen)

```bash
docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --cleanup \
  --interval 3600 \
  lernplan-reminder-bot
```

### Manuell

```bash
# Image aktualisieren
docker compose -f docker-compose.prod.yml pull

# Container neu starten
docker compose -f docker-compose.prod.yml up -d

# Alte Images aufräumen
docker image prune -f
```

### Auf Unraid

```bash
cd /mnt/user/appdata/LernplanReminderBot
docker compose pull
docker compose up -d
```

---

## 📊 Monitoring

### Logs ansehen

```bash
# Alle Logs
docker logs lernplan-reminder-bot

# Live-Logs (Follow)
docker logs -f lernplan-reminder-bot

# Letzte 100 Zeilen
docker logs --tail 100 lernplan-reminder-bot

# Logs mit Zeitstempel
docker logs -t lernplan-reminder-bot
```

### Container-Status

```bash
# Status prüfen
docker ps | grep lernplan

# Ressourcen-Nutzung
docker stats lernplan-reminder-bot

# Detaillierte Infos
docker inspect lernplan-reminder-bot
```

---

## 🐛 Troubleshooting

### Bot startet nicht

1. **Logs prüfen:**
   ```bash
   docker logs lernplan-reminder-bot
   ```

2. **Umgebungsvariablen prüfen:**
   ```bash
   docker exec lernplan-reminder-bot env
   ```

3. **Token validieren:**
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```

### Daten werden nicht gespeichert

```bash
# Volume prüfen
docker inspect lernplan-reminder-bot | grep -A 5 "Mounts"

# Berechtigungen prüfen (auf Host)
ls -la ./data/
```

### Container neu starten

```bash
# Graceful restart
docker compose restart lernplan-bot

# Hard restart
docker compose down
docker compose up -d

# Container ohne Cache neu bauen (nur bei lokalem Build)
docker compose build --no-cache
docker compose up -d
```

---

## 🔒 Sicherheit

### Best Practices

1. **Niemals Tokens in Code committen**
2. **.env immer in .gitignore**
3. **Nur notwendige Volumes mounten**
4. **Ressourcenlimits setzen** (siehe docker-compose.prod.yml)
5. **Regelmäßige Updates**

### Backup

```bash
# Daten-Backup erstellen
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Backup wiederherstellen
tar -xzf backup-YYYYMMDD.tar.gz
```

---

## 📝 Umgebungsvariablen

Siehe `.env.example` für vollständige Dokumentation:

| Variable | Erforderlich | Beispiel | Beschreibung |
|----------|--------------|----------|--------------|
| `TELEGRAM_TOKEN` | ✅ Ja | `123456:ABC...` | Bot Token von @BotFather |
| `STUDENT_CHAT_ID` | ✅ Ja | `123456789` | Chat-ID des Schülers |
| `PARENT_CHAT_ID` | ⚠️ Optional | `987654321` | Chat-ID Eltern/Betreuer |
| `DATA_DIR` | ⚠️ Optional | `data` | Datenverzeichnis (Standard: data) |
| `LOG_LEVEL` | ⚠️ Optional | `INFO` | Log-Level (DEBUG, INFO, WARNING, ERROR) |

---

## 🚀 GitHub Actions Auto-Deploy

Der Bot baut automatisch neue Images bei jedem Push auf `main`:

1. **Automatisch:** Jeder Push triggert CI/CD
2. **Versioniert:** Tags `v*` erstellen versioned Images
3. **Multi-Arch:** Unterstützt AMD64 und ARM64

**Image Tags:**
- `ghcr.io/portboy/lernplan-reminder-bot:latest` - Neueste Version
- `ghcr.io/portboy/lernplan-reminder-bot:main` - Main Branch
- `ghcr.io/portboy/lernplan-reminder-bot:v0.1.0` - Spezifische Version
- `ghcr.io/portboy/lernplan-reminder-bot:sha-abc1234` - Commit-basiert
