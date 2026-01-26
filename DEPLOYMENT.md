# Deployment Guide

## 🐳 Docker Deployment Optionen

### Option 1: Lokale Entwicklung (mit Build)
```bash
# .env erstellen (siehe .env.example)
cp .env.example .env
# .env mit TOKEN, CHAT IDs etc. füllen

# Container bauen und starten
docker compose up -d

# Logs verfolgen
docker compose logs -f

# Container stoppen
docker compose down
```

### Option 2: Produktion über docker-compose.prod.yml
```bash
cp .env.example .env
# Werte eintragen

docker compose -f docker-compose.prod.yml up -d
```

Updates:
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f
```

### Option 3: Unraid Server (empfohlen)

**Setup-Schritte:**

1. **Verzeichnisse erstellen**
   ```bash
   mkdir -p /mnt/user/appdata/LernplanReminderBot_v2/data
   ```

2. **.env anlegen**
   ```bash
   nano /mnt/user/appdata/LernplanReminderBot_v2/.env
   ```
   Inhalt:
   ```env
   TELEGRAM_TOKEN=your_token
   STUDENT_CHAT_ID=student_id
   PARENT_CHAT_ID=parent_id
   DATA_DIR=data
   LOG_LEVEL=INFO
   ```

3. **docker-compose.yml erstellen**
   ```bash
   nano /mnt/user/appdata/LernplanReminderBot_v2/docker-compose.yml
   ```
   Inhalt:
   ```yaml
   version: "3.9"
   services:
     lernplan-reminder-bot-v2:
       image: ghcr.io/portboy/lernplan-reminder-bot-v2:latest
       container_name: lernplan-reminder-bot-v2
       restart: unless-stopped
       env_file: /mnt/user/appdata/LernplanReminderBot_v2/.env
       volumes:
         - /mnt/user/appdata/LernplanReminderBot_v2/data:/app/data
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
   --env-file .env \
   -v $(pwd)/data:/app/data \
   ghcr.io/portboy/lernplan-reminder-bot-v2:latest
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
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
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
docker logs lernplan-reminder-bot-v2
docker logs -f lernplan-reminder-bot-v2
docker logs --tail 100 lernplan-reminder-bot-v2
docker logs -t lernplan-reminder-bot-v2
```

## 🐛 Troubleshooting

**Bot startet nicht**
```bash
docker logs lernplan-reminder-bot-v2
docker exec lernplan-reminder-bot-v2 env
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

**Daten werden nicht gespeichert**
```bash
docker inspect lernplan-reminder-bot-v2 | grep -A 5 "Mounts"
ls -la ./data/
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

1. Tokens niemals öffentlich committen
2. `.env` immer in `.gitignore`
3. Nur notwendige Volumes mounten
4. Ressourcenlimits (siehe docker-compose.prod.yml)
5. Regelmäßige Updates durchführen

### Backup
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz data/
```
