import os

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
MONGO_URL = os.getenv("MONGO_URL")

if TOKEN is None:
    raise ValueError("TOKEN environment variable missing!")

if ADMIN_ID is None:
    raise ValueError("ADMIN_ID environment variable missing!")

ADMIN_ID = int(ADMIN_ID)

DEFAULT_START = "👋 Welcome to Premium Bot"
DEFAULT_PRICE = "29"
