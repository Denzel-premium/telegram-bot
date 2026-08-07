import os
from pymongo import MongoClient
from config import MONGO_URL

client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]

# Collections
users_col = db["users"]
videos_col = db["videos"]
config_col = db["config"]
pending_col = db["pending"]
expiry_col = db["expiry"]

# CONFIG
def get_config(key):
    doc = config_col.find_one({"key": str(key).strip()})
    return doc["value"] if doc else None

def set_config(key, value):
    config_col.update_one({"key": str(key).strip()}, {"$set": {"value": value}}, upsert=True)

# USERS
def add_user(user_id):
    users_col.update_one({"user_id": int(user_id)}, {"$set": {"user_id": int(user_id)}}, upsert=True)

def get_all_users():
    return [u["user_id"] for u in users_col.find()]

def add_premium(user_id):
    users_col.update_one({"user_id": int(user_id)}, {"$set": {"premium": True}}, upsert=True)

def is_premium(user_id):
    u = users_col.find_one({"user_id": int(user_id)})
    return bool(u and u.get("premium"))

# PENDING REQUESTS
def add_pending(user_id, file_id):
    pending_col.update_one({"user_id": int(user_id)}, {"$set": {"file_id": file_id}}, upsert=True)

def get_pending():
    return list(pending_col.find())

def remove_pending(user_id):
    pending_col.delete_many({"user_id": int(user_id)})

# ================= VIDEOS & FOLDERS (SAFE FETCH) =================
def add_video(folder, file_id):
    clean_folder = str(folder).strip()
    videos_col.insert_one({"folder": clean_folder, "file_id": file_id})

def get_videos(folder):
    clean_folder = str(folder).strip()
    # Case-Insensitive Search: Capital ya Small mismatch ki wajah se kabhi video miss nahi hogi
    vids = list(videos_col.find({"folder": {"$regex": f"^{clean_folder}$", "$options": "i"}}))
    return vids

def get_folders():
    folders = videos_col.distinct("folder")
    # Clean unique folder names list
    clean_folders = []
    for f in folders:
        if f and str(f).strip():
            clean_f = str(f).strip()
            if clean_f not in clean_folders:
                clean_folders.append(clean_f)
    return clean_folders

def delete_folder(folder):
    clean_folder = str(folder).strip()
    videos_col.delete_many({"folder": {"$regex": f"^{clean_folder}$", "$options": "i"}})

def delete_video(folder, index):
    vids = get_videos(folder)
    if 0 <= index < len(vids):
        videos_col.delete_one({"_id": vids[index]["_id"]})

# ================= EXPIRY SYSTEM =================
def set_expiry(user_id, message_ids, chat_id, expiry_time):
    expiry_col.insert_one({
        "user_id": int(user_id),
        "message_ids": message_ids,
        "chat_id": chat_id,
        "expiry_time": expiry_time
    })

def get_expired(now):
    return list(expiry_col.find({"expiry_time": {"$lte": now}}))

def delete_expiry(_id):
    expiry_col.delete_one({"_id": _id})
