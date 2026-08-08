import os
from pymongo import MongoClient

# ================= MONGO SETUP =================
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGO_URI")

if not MONGO_URL:
    try:
        from config import MONGO_URL
    except ImportError:
        MONGO_URL = None

if not MONGO_URL:
    raise Exception("❌ MONGO_URL not set in ENV or config.py")

client = MongoClient(MONGO_URL)

db = client["bot_db"]

users = db["users"]
videos = db["videos"]
config = db["config"]
pending = db["pending"]
exp = db["expiry"]


# ================= CONFIG =================
def set_config(key, value):
    config.update_one({"key": str(key).strip()}, {"$set": {"value": value}}, upsert=True)

def get_config(key):
    data = config.find_one({"key": str(key).strip()})
    return data["value"] if data else None


# ================= USERS & PERMISSIONS =================
def add_user(user_id):
    users.update_one({"user_id": int(user_id)}, {"$set": {"user_id": int(user_id)}}, upsert=True)

def get_all_users():
    return [u["user_id"] for u in users.find()]

def add_premium(user_id):
    users.update_one(
        {"user_id": int(user_id)},
        {"$set": {"premium": True}},
        upsert=True
    )

def remove_premium(user_id):
    users.update_one(
        {"user_id": int(user_id)},
        {"$set": {"premium": False}},
        upsert=True
    )

def is_premium(user_id):
    user = users.find_one({"user_id": int(user_id)})
    return bool(user and user.get("premium"))

def grant_folder_access_db(user_id, folder_name):
    clean_folder = str(folder_name).strip()
    users.update_one(
        {"user_id": int(user_id)},
        {"$addToSet": {"folder_passes": clean_folder}},
        upsert=True
    )

def revoke_folder_access_db(user_id, folder_name):
    clean_folder = str(folder_name).strip()
    users.update_one(
        {"user_id": int(user_id)},
        {"$pull": {"folder_passes": clean_folder}}
    )

def has_folder_access_db(user_id, folder_name):
    clean_folder = str(folder_name).strip()
    u = users.find_one({"user_id": int(user_id)})
    if u and "folder_passes" in u and isinstance(u["folder_passes"], list):
        passes = [str(x).strip().lower() for x in u["folder_passes"]]
        return clean_folder.lower() in passes
    return False


# ================= PENDING =================
def add_pending(user_id, file_id):
    pending.update_one({"user_id": int(user_id)}, {"$set": {"file_id": file_id}}, upsert=True)

def get_pending():
    return list(pending.find())

def remove_pending(user_id):
    pending.delete_many({"user_id": int(user_id)})


# ================= VIDEOS =================
def add_video(folder, file_id):
    clean_folder = str(folder).strip()
    if not videos.find_one({"file_id": file_id}):
        videos.insert_one({
            "folder": clean_folder,
            "file_id": file_id
        })

def get_folders():
    folders = videos.distinct("folder")
    return [str(f).strip() for f in folders if f and str(f).strip()]

def get_videos(folder):
    clean_folder = str(folder).strip()
    vids = list(videos.find({"folder": clean_folder}).sort("_id", -1))
    if not vids:
        vids = list(videos.find({"folder": {"$regex": f"^{clean_folder}$", "$options": "i"}}).sort("_id", -1))
    return vids

def delete_folder(name):
    clean_folder = str(name).strip()
    videos.delete_many({"folder": {"$regex": f"^{clean_folder}$", "$options": "i"}})

def delete_video(folder, index):
    data = get_videos(folder)
    if 0 <= index < len(data):
        videos.delete_one({"_id": data[index]["_id"]})

def rename_folder(old_name, new_name):
    videos.update_many(
        {"folder": str(old_name).strip()},
        {"$set": {"folder": str(new_name).strip()}}
    )

def search_video(keyword):
    return list(videos.find({"file_id": {"$regex": keyword}}))

def count_videos(folder):
    return len(get_videos(folder))


# ================= EXPIRY SYSTEM =================
def set_expiry(user_id, message_ids, chat_id, expire_at):
    exp.insert_one({
        "user_id": int(user_id),
        "message_ids": list(message_ids),
        "chat_id": chat_id,
        "expire_at": expire_at
    })

def get_expired(now):
    return list(exp.find({"expire_at": {"$lte": now}}))

def delete_expiry(_id):
    exp.delete_one({"_id": _id})
