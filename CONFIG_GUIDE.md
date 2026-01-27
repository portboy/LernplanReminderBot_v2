# Configuration Management Guide

## 📋 Overview

The bot can be fully configured via JSON files **without redeployment**. Simply edit the config and restart the container.

## 🔧 Configuration Files

### Primary: `userconfig/bot_config.json`

This is the main configuration file. All settings can be changed here.

```json
{
  "telegram_token": "YOUR_BOT_TOKEN",
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
    }
  ],
  
  "dynamic_planning_times": ["07:30", "09:00", "14:00", "16:30", "18:30", "20:30"],
  "duration_choices": [15, 30, 45, 60, 90, 120],
  "min_minutes": 1,
  "max_minutes": 180,
  "jokers_per_week": 1,
  
  "morning_prompt_time": "07:30",
  "daily_check_time": "20:00",
  
  "horse_happy_images": [
    "https://images.pexels.com/photos/1996333/pexels-photo-1996333.jpeg"
  ],
  "sad_gifs": [
    "https://media.giphy.com/media/3oz8xKaR836UJOYeOc/giphy.gif"
  ]
}
```

### Secondary: `.env` (optional)

Environment variables override JSON config values:

```bash
TELEGRAM_TOKEN=your_token_here
STUDENT_CHAT_ID=123456789
PARENT_CHAT_ID=987654321
TIMEZONE=Europe/Berlin
LOG_LEVEL=DEBUG
```

## 🎨 Common Configuration Tasks

### Adding a New Subject

Edit `userconfig/bot_config.json`:

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

**Apply**: `docker-compose restart`

### Changing Reminder Times

```json
{
  "morning_prompt_time": "08:00",
  "daily_check_time": "21:00"
}
```

**Apply**: `docker-compose restart`

### Adjusting Planning Time Options

```json
{
  "dynamic_planning_times": ["08:00", "10:00", "12:00", "15:00", "18:00", "21:00"]
}
```

**Apply**: `docker-compose restart`

### Customizing Duration Choices

```json
{
  "duration_choices": [10, 20, 30, 45, 60, 90]
}
```

**Apply**: `docker-compose restart`

### Changing Media URLs

```json
{
  "horse_happy_images": [
    "https://your-cdn.com/happy-horse-1.jpg",
    "https://your-cdn.com/happy-horse-2.jpg"
  ],
  "sad_gifs": [
    "https://your-cdn.com/sad-1.gif"
  ]
}
```

**Apply**: `docker-compose restart`

### Setting Study Time Limits

```json
{
  "min_minutes": 5,
  "max_minutes": 240
}
```

**Apply**: `docker-compose restart`

### Adjusting Joker System

```json
{
  "jokers_per_week": 2
}
```

**Apply**: `docker-compose restart`

## 🐳 Docker Configuration

### Volume Mounting

In `docker-compose.yml`:

```yaml
volumes:
  - ./data:/app/data              # User data (required)
  - ./userconfig:/app/userconfig  # Configuration (required)
```

### Environment Variables

Priority order:
1. Command-line args (not used currently)
2. Environment variables (`.env` or docker env)
3. JSON config (`userconfig/bot_config.json`)
4. Default values

## 🔄 Hot-Reload Workflow

1. Edit `userconfig/bot_config.json`
2. Save the file
3. Restart container: `docker-compose restart`
4. Bot loads new config (< 5 seconds)

**No rebuild needed!**

## ✅ Configuration Validation

The bot validates configuration on startup. Invalid values will prevent startup with clear error messages.

### Test Configuration

```bash
# Validate JSON syntax
python -c "import json; json.load(open('userconfig/bot_config.json'))"

# Test bot config loading
python -c "from core.config import load_config; config = load_config(); print('Config OK')"
```

## 🔒 Security Best Practices

### 1. Never commit secrets

Add to `.gitignore`:
```
userconfig/bot_config.json
.env
```

### 2. Use environment variables in production

```bash
# Set via Docker
docker run -e TELEGRAM_TOKEN="secret_token" ...

# Or via docker-compose
environment:
  - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
```

### 3. Restrict file permissions

```bash
chmod 600 userconfig/bot_config.json
chmod 600 .env
```

## 📊 Monitoring Configuration Changes

Enable DEBUG logging to see config loading:

```json
{
  "log_level": "DEBUG"
}
```

Logs will show:
```
Loading configuration from userconfig/bot_config.json
Successfully loaded config from userconfig/bot_config.json
Configuration loaded and validated successfully
```

## 🆘 Troubleshooting

### "Configuration validation failed"

**Cause**: Invalid JSON or validation error

**Fix**:
```bash
# Check JSON syntax
python -c "import json; json.load(open('userconfig/bot_config.json'))"

# Check for common errors:
# - Missing comma
# - Unclosed brackets
# - Invalid time format (must be HH:MM)
# - Negative chat_id
```

### Changes not applied

**Cause**: Container not restarted

**Fix**:
```bash
docker-compose restart
# or
docker restart lernplan-reminder-bot-v2
```

### Config file not found

**Cause**: File not in expected location or not mounted

**Fix**:
1. Create: `userconfig/bot_config.json`
2. Check docker-compose volumes
3. Run migration script: `python scripts/migrate_v2.py`

## 📝 Configuration Reference

### Required Fields

- `telegram_token`: Your bot token from BotFather

### Optional Fields (with defaults)

- `student_chat_id`: null
- `parent_chat_id`: null
- `timezone`: "Europe/Berlin"
- `log_level`: "INFO"
- `data_dir`: "data"
- `allowed_subjects`: [Mathe, Englisch]
- `dynamic_planning_times`: [07:30, 09:00, 14:00, 16:30, 18:30, 20:30]
- `duration_choices`: [15, 30, 45, 60, 90, 120]
- `min_minutes`: 1
- `max_minutes`: 180
- `jokers_per_week`: 1
- `morning_prompt_time`: "07:30"
- `daily_check_time`: "20:00"

## 🔗 Related Documentation

- [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md) - Migration from v1
- [README.md](README.md) - General documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment options
