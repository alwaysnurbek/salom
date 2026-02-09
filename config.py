import os
import logging
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Parse comma-separated IDs into a set of integers
admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
ADMIN_USER_IDS = set()
for x in admin_ids_str.split(","):
    x = x.strip()
    if x.isdigit():
        ADMIN_USER_IDS.add(int(x))

TIMEZONE = os.getenv("TIMEZONE", "UTC")

# Database path (Backward compatibility or local fallback)
DB_PATH = "bluebot.db"
DATABASE_URL = os.getenv("DATABASE_URL")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    logger.warning("BOT_TOKEN is not set in .env")

# Channel Subscription
REQUIRED_CHANNEL_ID = "-1002659222713"
REQUIRED_CHANNEL_USERNAME = "BluePrep_Academy"
