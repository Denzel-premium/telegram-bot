import os

TOKEN = os.getenv("TOKEN")
if TOKEN:
    TOKEN = TOKEN.strip()

ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else 0
