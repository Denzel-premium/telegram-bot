from pymongo import MongoClient

client = MongoClient("MONGO_URL")
db = client["bot_db"]

users = db["users"]
videos = db["videos"]
config = db["config"]
pending = db["pending"]

# ---------- CONFIG ----------
def set_config(key, value):
    config.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

def get_config(key):
    data = config.find_one({"key": key})
    return data["value"] if data else None

# ---------- USERS ----------
def add_premium(user_id):
    users.update_one(
        {"user_id": user_id},
        {"$set": {"premium": True}},
        upsert=True
    )

def is_premium(user_id):
    user = users.find_one({"user_id": user_id})
    return user and user.get("premium")

# ---------- PENDING ----------
def add_pending(user_id, file_id):
    pending.insert_one({"user_id": user_id, "file_id": file_id})

def get_pending():
    return list(pending.find())

def remove_pending(user_id):
    pending.delete_many({"user_id": user_id})

# ---------- VIDEOS ----------
def add_video(folder, file_id):
    videos.insert_one({
        "folder": folder,
        "file_id": file_id
    })

def get_folders():
    return videos.distinct("folder")

def get_videos(folder):
    return list(videos.find({"folder": folder}))
