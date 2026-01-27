#!/bin/bash
# Quick setup script for LernplanReminderBot v2

set -e

echo "=================================="
echo "LernplanReminderBot v2 Setup"
echo "=================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11 or higher."
    exit 1
fi

# Run migration script
echo "🔄 Running migration preparation..."
python3 scripts/migrate_v2.py

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit userconfig/bot_config.json"
echo "   - Set your TELEGRAM_TOKEN"
echo "   - Set STUDENT_CHAT_ID"
echo "   - Set PARENT_CHAT_ID (optional)"
echo ""
echo "2. Build and start:"
echo "   docker-compose build"
echo "   docker-compose up -d"
echo ""
echo "3. Check logs:"
echo "   docker-compose logs -f"
echo ""
echo "For more info, see:"
echo "- CONFIG_GUIDE.md"
echo "- UPGRADE_GUIDE.md"
echo ""
