from pymongo import MongoClient
import time

client = MongoClient("YOUR_MONGO_URL")
db = client["premium_bot"]

pending = db["pending"]
approved = db["approved"]
premium = db["premium"]
temp_access = db["temp_access"]


# ================= PREMIUM =================
def add_premium(user_id):
    premium.update_one(
        {"user_id": user_id},
        {"$set": {"premium": True}},
        upsert=True
    )

def is_premium(user_id):
    return premium.find_one({"user_id": user_id}) is not None


# ================= PENDING =================
def add_pending(user_id, file_id):
    pending.update_one(
        {"user_id": user_id},
        {"$set": {"file_id": file_id}},
        upsert=True
    )

def get_pending():
    return list(pending.find())

def remove_pending(user_id):
    pending.delete_one({"user_id": user_id})


# ================= APPROVED =================
def set_approved(user_id, key):
    approved.update_one(
        {"user_id": user_id},
        {"$set": {"key": key}},
        upsert=True
    )

def get_key(user_id):
    data = approved.find_one({"user_id": user_id})
    return data["key"] if data else None


# ================= TEMP ACCESS (15 MIN) =================
def give_temp_access(user_id):
    temp_access.update_one(
        {"user_id": user_id},
        {"$set": {"start_time": time.time()}},
        upsert=True
    )

def can_access(user_id):
    data = temp_access.find_one({"user_id": user_id})

    if not data:
        return False

    return (time.time() - data["start_time"]) <= 900  # 15 min
