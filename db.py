from pymongo import MongoClient
import time
import os

MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(MONGO_URL)
db = client["premium_bot"]

# ================= COLLECTIONS =================
pending = db["pending"]
approved = db["approved"]
premium = db["premium"]
temp_access = db["temp_access"]
config = db["config"]
folders_col = db["folders"]   # 🔥 folder system added

# ================= CONFIG =================
def set_config(key, value):
    config.update_one(
        {"key": key},
        {"$set": {"value": value}},
        upsert=True
    )

def get_config(key, default=None):
    data = config.find_one({"key": key})
    return data["value"] if data else default

# ================= PAYMENT =================
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

# ================= APPROVAL =================
def set_approved(user_id, key):
    approved.update_one(
        {"user_id": user_id},
        {"$set": {"key": key}},
        upsert=True
    )

def get_key(user_id):
    data = approved.find_one({"user_id": user_id})
    return data["key"] if data else None

# ================= PREMIUM =================
def add_premium(user_id):
    premium.update_one(
        {"user_id": user_id},
        {"$set": {"premium": True}},
        upsert=True
    )

def is_premium(user_id):
    return premium.find_one({"user_id": user_id}) is not None

# ================= TEMP ACCESS =================
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
    return (time.time() - data["start_time"]) <= 900

# ================= FOLDER SYSTEM (FIXED + SAFE) =================

def create_folder(name):
    folders_col.update_one(
        {"name": name},
        {"$set": {"videos": []}},
        upsert=True
    )

def add_video(folder, file_id):
    folders_col.update_one(
        {"name": folder},
        {"$push": {"videos": file_id}},
        upsert=True
    )

def get_folder(folder):
    data = folders_col.find_one({"name": folder})
    return data.get("videos", []) if data else []

def list_folders():
    return [f["name"] for f in folders_col.find()]

def delete_folder(folder):
    folders_col.delete_one({"name": folder})
