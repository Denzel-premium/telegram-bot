import telebot
import time
import threading
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from config import TOKEN, ADMIN_ID, DEFAULT_START, DEFAULT_PRICE
from db import *

bot = telebot.TeleBot(TOKEN)

current_folder = None

# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📂 Video List")
    kb.add("💰 Buy Premium")

    text = get_config("start_text", DEFAULT_START)
    price = get_config("price", DEFAULT_PRICE)

    bot.send_message(
        msg.chat.id,
        f"{text}\n\n💰 Price: ₹{price}",
        reply_markup=kb
    )

# ================= MENU =================
@bot.message_handler(func=lambda m: m.text == "📂 Video List")
def videos(msg):
    folders = get_folders()

    if not folders:
        bot.send_message(msg.chat.id, "No videos available")
        return

    kb = InlineKeyboardMarkup()

    for f in folders:
        kb.add(InlineKeyboardButton(f["name"], callback_data=f"folder_{f['name']}"))

    bot.send_message(msg.chat.id, "Select folder:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "💰 Buy Premium")
def buy(msg):
    link = get_config("buy_link", "Not set")
    bot.send_message(msg.chat.id, f"Buy here:\n{link}")

# ================= SEND VIDEOS =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("folder_"))
def send_videos(call):
    folder = call.data.split("_",1)[1]
    videos = get_videos(folder)

    for v in videos:
        msg = bot.send_video(call.message.chat.id, v)
        auto_delete(call.message.chat.id, msg.message_id, 900)

def auto_delete(chat_id, msg_id, delay):
    def task():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    threading.Thread(target=task).start()

# ================= ADMIN =================
@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    bot.send_message(msg.chat.id,
        "/setstart text\n/setprice 29\n/setbuy link\n/addfolder name\n/addvideo folder"
    )

@bot.message_handler(commands=['setstart'])
def setstart(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("start_text", msg.text.replace("/setstart ",""))
    bot.reply_to(msg, "Start text updated")

@bot.message_handler(commands=['setprice'])
def setprice(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("price", msg.text.split(" ",1)[1])
    bot.reply_to(msg, "Price updated")

@bot.message_handler(commands=['setbuy'])
def setbuy(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("buy_link", msg.text.split(" ",1)[1])
    bot.reply_to(msg, "Buy link updated")

@bot.message_handler(commands=['addfolder'])
def addfolder(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    name = msg.text.split(" ",1)[1]
    add_folder(name)
    bot.reply_to(msg, "Folder added")

@bot.message_handler(commands=['addvideo'])
def set_folder(msg):
    global current_folder
    if msg.from_user.id != ADMIN_ID:
        return

    current_folder = msg.text.split(" ",1)[1]
    bot.reply_to(msg, f"Send videos for {current_folder}")

@bot.message_handler(content_types=['video'])
def save_video(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    add_video(current_folder, msg.video.file_id)
    bot.reply_to(msg, "Video saved")

# ================= RUN =================
print("Bot running...")
bot.polling()
