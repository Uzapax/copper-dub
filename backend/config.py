import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env if exists
env_path = BASE_DIR / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Telegram API credentials (get from https://my.telegram.org)
TG_API_ID = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")

# Telegram Bot Token (get from @BotFather) or leave empty if using phone session
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")

# Channel username or ID
TG_CHANNEL = os.getenv("TG_CHANNEL", "gygdub")

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Database path
DB_PATH = BASE_DIR / "copperdub.db"

# Session path for Telethon
SESSION_PATH = BASE_DIR / "copperdub_session"
