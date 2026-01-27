# Docker Image Tags & Branches

## 🏷️ Verfügbare Image-Tags

Der CI/CD Workflow baut automatisch für **jeden Branch** ein Docker Image.

### Haupttags:

| Tag | Branch | Verwendung | Stabilität |
|-----|--------|------------|-----------|
| `:latest` | `main` | **Production** | ✅ Stabil |
| `:main` | `main` | Production | ✅ Stabil |
| `:develop` | `develop` | **Testing** | ⚠️ Beta |
| `:<branch>` | Feature-Branch | Development | 🧪 Experimental |

## 📦 Image-Auswahl

### Production (empfohlen):
```yaml
image: ghcr.io/portboy/lernplan-reminder-bot-v2:latest
```

### Testing (neueste Features):
```yaml
image: ghcr.io/portboy/lernplan-reminder-bot-v2:develop
```

### Spezifischer Branch:
```yaml
image: ghcr.io/portboy/lernplan-reminder-bot-v2:feature-new-subjects
```

## 🔄 Wechseln zwischen Tags

### 1. Via docker-compose.yml bearbeiten:

```bash
# Editiere die Datei
nano docker-compose.ghcr.yml

# Ändere Zeile:
# von: image: ghcr.io/portboy/lernplan-reminder-bot-v2:latest
# zu:  image: ghcr.io/portboy/lernplan-reminder-bot-v2:develop

# Pull & Restart
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

### 2. Via Environment Variable:

```yaml
# In docker-compose.yml:
services:
  bot:
    image: ghcr.io/portboy/lernplan-reminder-bot-v2:${BOT_VERSION:-latest}
```

```bash
# Dann im Terminal:
export BOT_VERSION=develop
docker compose up -d

# Oder direkt:
BOT_VERSION=develop docker compose up -d
```

## 🚀 Typische Workflows

### Production Deployment:
```bash
# 1. Setup mit latest
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d

# 2. Updates checken
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

### Testing neuer Features:
```bash
# 1. Wechsel zu develop
# Editiere docker-compose.ghcr.yml: :latest → :develop

# 2. Pull & Start
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d

# 3. Testen...

# 4. Zurück zu stable
# Editiere docker-compose.ghcr.yml: :develop → :latest
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

### Feature-Branch testen:
```bash
# Entwickler hat Branch "feature-multi-language" erstellt
# Image wird automatisch gebaut als :feature-multi-language

# Editiere docker-compose.ghcr.yml:
# image: ghcr.io/portboy/lernplan-reminder-bot-v2:feature-multi-language

docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

## 🔍 Welche Tags gibt es?

### Via GitHub Container Registry:
```bash
# Browser öffnen:
https://github.com/portboy/LernplanReminderBot_v2/pkgs/container/lernplan-reminder-bot-v2
```

### Via Docker CLI:
```bash
# Alle Tags anzeigen (benötigt ghcr.io Login)
docker pull ghcr.io/portboy/lernplan-reminder-bot-v2:latest
docker images | grep lernplan-reminder-bot-v2
```

## 📊 Branch-Strategie

```
main (latest)
  ├─ Production-ready
  ├─ Thoroughly tested
  └─ Manual deployments

develop
  ├─ Integration Branch
  ├─ Latest features
  └─ Automated testing

feature/<name>
  ├─ Feature development
  ├─ Experimental
  └─ Per-branch images
```

## ⚙️ CI/CD Pipeline

Workflow baut automatisch Images für:
- ✅ Push zu `main` → `:latest` + `:main`
- ✅ Push zu `develop` → `:develop`
- ✅ Push zu Feature-Branch → `:<branch-name>`
- ✅ Pull Requests → `:pr-<number>` (optional)

## 🆘 Troubleshooting

### Image nicht gefunden:
```bash
# Prüfe verfügbare Tags
docker search ghcr.io/portboy/lernplan-reminder-bot-v2

# Oder auf GitHub:
https://github.com/portboy/LernplanReminderBot_v2/pkgs/container/lernplan-reminder-bot-v2
```

### Falsches Image läuft:
```bash
# Aktuelles Image prüfen
docker inspect lernplan-reminder-bot-v2 | grep Image

# Force Pull
docker compose -f docker-compose.ghcr.yml pull --no-cache
docker compose -f docker-compose.ghcr.yml up -d --force-recreate
```

### Rollback zu älterer Version:
```bash
# Option 1: Zurück zu latest
# Editiere docker-compose.ghcr.yml: :<tag> → :latest

# Option 2: Spezifische Version (falls getaggt)
# image: ghcr.io/portboy/lernplan-reminder-bot-v2:v2.0.1

docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

## 📝 Best Practices

1. **Production**: Immer `:latest` oder `:main` verwenden
2. **Testing**: `:develop` in separater Umgebung testen
3. **Features**: Feature-Branch-Tags nur temporär für Tests
4. **Pinning**: Für kritische Deployments spezifische Versions-Tags verwenden
5. **Updates**: Regelmäßig `docker compose pull` ausführen

## 🔗 Weitere Infos

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment-Optionen
- [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md) - Migrations-Anleitung
- [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - Konfiguration
