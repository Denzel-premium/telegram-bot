import os

# ================= TELEGRAM =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ================= DEFAULT VALUES =================
DEFAULT_START = "👋 Welcome to Premium Bot"
DEFAULT_PRICE = "29"

# ================= MONGO =================
MONGO_URL = os.getenv("MONGO_URL")
