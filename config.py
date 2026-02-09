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

# FIX: Sanitize URL and force IPv4 resolution for Supabase on Railway
if DATABASE_URL:
    # 1. Remove brackets if user accidentally included them around password
    DATABASE_URL = DATABASE_URL.replace('[', '').replace(']', '')
    
    # 2. Force IPv4 resolution to avoid "Network is unreachable" on IPv6
    try:
        from urllib.parse import urlparse, urlunparse
        import socket
        
        parsed = urlparse(DATABASE_URL)
        if parsed.hostname:
            ipv4_address = socket.gethostbyname(parsed.hostname)
            # Replace hostname with resolved IPv4 address
            DATABASE_URL = DATABASE_URL.replace(parsed.hostname, ipv4_address)
            logging.info(f"Resolved database host {parsed.hostname} to {ipv4_address}")
            
    except Exception as e:
        logging.warning(f"Failed to resolve database hostname to IPv4: {e}")

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
