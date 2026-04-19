import os

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
MONGO_URL = os.getenv("MONGO_URL")

# clean TOKEN
if TOKEN:
    TOKEN = TOKEN.strip()
else:
    TOKEN = None

# admin convert
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else 0

if not MONGO_URL:
    raise Exception("❌ MONGO_URL missing in Railway ENV")
DEFAULT_START = "👋 Welcome to Premium Bot"
DEFAULT_PRICE = "29"
