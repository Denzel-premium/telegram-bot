import os
from pymongo import MongoClient

# ================= MONGO SETUP =================
MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise Exception("❌ MONGO_URL not set in Railway ENV")

client = MongoClient(MONGO_URL)

db = client["bot_db"]

users = db["users"]
videos = db["videos"]
config = db["config"]
pending = db["pending"]

# ✅ EXPIRY COLLECTION
exp = db["expiry"]


# ================= CONFIG =================
def set_config(key, value):
    config.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

def get_config(key):
    data = config.find_one({"key": key})
    return data["value"] if data else None


# ================= USERS =================
def add_premium(user_id):
    users.update_one(
        {"user_id": user_id},
        {"$set": {"premium": True}},
        upsert=True
    )

def is_premium(user_id):
    user = users.find_one({"user_id": user_id})
    return user and user.get("premium")


# ================= PENDING =================
def add_pending(user_id, file_id):
    pending.insert_one({"user_id": user_id, "file_id": file_id})

def get_pending():
    return list(pending.find())

def remove_pending(user_id):
    pending.delete_many({"user_id": user_id})


# ================= VIDEOS =================
def add_video(folder, file_id):
    if not videos.find_one({"file_id": file_id}):
        videos.insert_one({
            "folder": folder,
            "file_id": file_id
        })

def get_folders():
    return videos.distinct("folder")

def get_videos(folder):
    return list(videos.find({"folder": folder}).sort("_id", -1))

def delete_folder(name):
    videos.delete_many({"folder": name})

def delete_video(folder, index):
    data = list(videos.find({"folder": folder}).sort("_id", -1))
    if 0 <= index < len(data):
        videos.delete_one({"_id": data[index]["_id"]})


def rename_folder(old_name, new_name):
    videos.update_many(
        {"folder": old_name},
        {"$set": {"folder": new_name}}
    )


def search_video(keyword):
    return list(videos.find({"file_id": {"$regex": keyword}}))

def count_videos(folder):
    return videos.count_documents({"folder": folder})


# ================= EXPIRY SYSTEM =================
def set_expiry(user_id, message_ids, chat_id, expire_at):
    exp.insert_one({
        "user_id": user_id,
        "message_ids": list(message_ids),  # ✅ SAFE COPY FIX
        "chat_id": chat_id,
        "expire_at": expire_at
    })


def get_expired(now):
    return list(exp.find({"expire_at": {"$lte": now}}))


# ❗ MAIN FIX HERE
def delete_expiry(_id):
    exp.delete_one({"_id": _id})
