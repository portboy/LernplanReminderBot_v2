"""Migration script for v1 to v2."""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def migrate_data_files(data_dir: Path) -> None:
    """Migrate old user files to new anonymized format."""
    LOGGER.info(f"Checking for old format files in {data_dir}")
    
    migrated = 0
    for old_file in data_dir.glob("user_*.json"):
        if old_file.name == "id_mapping.json":
            continue
        
        try:
            # Extract chat_id from filename
            parts = old_file.stem.split("_", 1)
            if len(parts) != 2:
                continue
            
            try:
                chat_id = int(parts[1])
            except ValueError:
                # Already in new format (hash)
                continue
            
            LOGGER.info(f"Found old format file: {old_file.name}")
            LOGGER.info(f"This file will be automatically migrated on first access")
            migrated += 1
            
        except Exception as e:
            LOGGER.error(f"Error processing {old_file}: {e}")
    
    if migrated > 0:
        LOGGER.info(f"Found {migrated} files in old format")
        LOGGER.info("These will be automatically migrated when the bot accesses them")
    else:
        LOGGER.info("No old format files found")


def create_config_template(config_path: Path) -> None:
    """Create a config template if it doesn't exist."""
    if config_path.exists():
        LOGGER.info(f"Config file already exists: {config_path}")
        return
    
    template = {
        "telegram_token": "YOUR_BOT_TOKEN_HERE",
        "student_chat_id": None,
        "parent_chat_id": None,
        "timezone": "Europe/Berlin",
        "log_level": "INFO",
        "data_dir": "data",
        "config_dir": "userconfig",
        "allowed_subjects": [
            {"name": "Mathe", "emoji": "🔢", "color": "#FF6B6B"},
            {"name": "Englisch", "emoji": "🇬🇧", "color": "#4ECDC4"},
            {"name": "Deutsch", "emoji": "📝", "color": "#95E1D3"},
            {"name": "Physik", "emoji": "⚛️", "color": "#F38181"},
        ],
        "dynamic_planning_times": ["07:30", "09:00", "14:00", "16:30", "18:30", "20:30"],
        "duration_choices": [15, 30, 45, 60, 90, 120],
        "min_minutes": 1,
        "max_minutes": 180,
        "jokers_per_week": 1,
        "morning_prompt_time": "07:30",
        "daily_check_time": "20:00",
        "horse_happy_images": [
            "https://images.pexels.com/photos/1996333/pexels-photo-1996333.jpeg",
            "https://images.pexels.com/photos/52500/horse-herd-fog-nature-52500.jpeg",
            "https://images.pexels.com/photos/2749423/pexels-photo-2749423.jpeg",
        ],
        "sad_gifs": [
            "https://media.giphy.com/media/3oz8xKaR836UJOYeOc/giphy.gif",
            "https://media.giphy.com/media/l3vR9O6r8n6u7q1lS/giphy.gif",
            "https://media.giphy.com/media/9Y5BbDSkSTiY8/giphy.gif",
        ],
    }
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    LOGGER.info(f"✅ Created config template: {config_path}")
    LOGGER.info("⚠️  Please edit the file and set your bot token and chat IDs!")


def check_env_file() -> None:
    """Check if .env file exists and show info."""
    env_file = Path(".env")
    if env_file.exists():
        LOGGER.info("Found .env file")
        LOGGER.info("Note: Environment variables will override bot_config.json values")
    else:
        LOGGER.info("No .env file found (using only bot_config.json)")


def main() -> int:
    """Run migration."""
    LOGGER.info("=" * 60)
    LOGGER.info("LernplanReminderBot v2 Migration Tool")
    LOGGER.info("=" * 60)
    
    # Find repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    # Check data directory
    data_dir = repo_root / "data"
    if data_dir.exists():
        migrate_data_files(data_dir)
    else:
        LOGGER.info("No data directory found (will be created on first run)")
    
    # Create config template
    config_path = repo_root / "userconfig" / "bot_config.json"
    create_config_template(config_path)
    
    # Check .env
    check_env_file()
    
    LOGGER.info("=" * 60)
    LOGGER.info("Migration preparation complete!")
    LOGGER.info("")
    LOGGER.info("Next steps:")
    LOGGER.info("1. Edit userconfig/bot_config.json with your bot token and chat IDs")
    LOGGER.info("2. Review the allowed_subjects and adjust as needed")
    LOGGER.info("3. Run: docker-compose build && docker-compose up -d")
    LOGGER.info("")
    LOGGER.info("Old data files will be automatically migrated on first access.")
    LOGGER.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
