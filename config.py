import os

# ================= TELEGRAM =================
TOKEN = os.getenv("TOKEN")

ADMIN_ID = os.getenv("ADMIN_ID")

if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
else:
    ADMIN_ID = 0

# ================= MONGO =================
MONGO_URL = os.getenv("MONGO_URL")

# ================= DEFAULT SETTINGS =================
DEFAULT_START = "👋 Welcome to Premium Bot"
DEFAULT_PRICE = "29"
