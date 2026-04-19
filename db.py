from pymongo import MongoClient
from config import MONGO_URL

client = MongoClient(MONGO_URL)
db = client["telegram_bot"]

config_col = db["config"]
folder_col = db["folders"]

# -------- CONFIG --------
def set_config(key, value):
    config_col.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

def get_config(key, default=None):
    data = config_col.find_one({"key": key})
    return data["value"] if data else default

# -------- FOLDER --------
def add_folder(name):
    folder_col.update_one({"name": name}, {"$set": {"videos": []}}, upsert=True)

def add_video(folder, file_id):
    folder_col.update_one({"name": folder}, {"$push": {"videos": file_id}})

def get_folders():
    return list(folder_col.find())

def get_videos(folder):
    data = folder_col.find_one({"name": folder})
    return data["videos"] if data else []
