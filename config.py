import os

# ================= TELEGRAM =================
TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else None

# ================= MONGO =================
MONGO_URL = os.getenv("MONGO_URL")

# ================= DEFAULT SETTINGS =================
DEFAULT_START = "👋 Welcome to Premium Bot"
DEFAULT_PRICE = "29"

if not TOKEN:
    raise Exception("❌ BOT_TOKEN missing in Railway ENV")

if not ADMIN_ID:
    raise Exception("❌ ADMIN_ID missing in Railway ENV")
