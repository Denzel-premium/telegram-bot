import telebot
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

from config import TOKEN, ADMIN_ID
from db import *

bot = telebot.TeleBot(TOKEN)

# -------- START --------
@bot.message_handler(commands=['start'])
def start(msg):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📂 Video List")
    kb.add("💰 Buy Premium")

    text = get_config("start_text", "Welcome to Denzel Premium")
    price = get_config("price", "29")

    bot.send_message(msg.chat.id, f"{text}\n\nPrice: ₹{price}", reply_markup=kb)

# -------- MENU --------
@bot.message_handler(func=lambda m: m.text == "📂 Video List")
def show_folders(msg):
    folders = get_folders()

    if not folders:
        bot.send_message(msg.chat.id, "No videos yet")
        return

    kb = InlineKeyboardMarkup()
    for f in folders:
        kb.add(InlineKeyboardButton(f["name"], callback_data=f"folder_{f['name']}"))

    bot.send_message(msg.chat.id, "Select folder:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "💰 Buy Premium")
def buy(msg):
    link = get_config("buy_link", "Not set")
    bot.send_message(msg.chat.id, f"Buy here:\n{link}")

# -------- VIDEO SEND --------
@bot.callback_query_handler(func=lambda c: c.data.startswith("folder_"))
def send_videos(call):
    folder = call.data.split("_",1)[1]
    videos = get_videos(folder)

    for v in videos:
        msg = bot.send_video(call.message.chat.id, v)
        delete_after(call.message.chat.id, msg.message_id, 900)

def delete_after(chat_id, message_id, delay):
    def task():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
    threading.Thread(target=task).start()

# -------- ADMIN --------
@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    bot.send_message(msg.chat.id,
        "/setstart text\n/setprice 29\n/setbuy link\n/addfolder name\n/addvideo name"
    )

@bot.message_handler(commands=['setstart'])
def setstart(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("start_text", msg.text.replace("/setstart ",""))
    bot.reply_to(msg, "Done")

@bot.message_handler(commands=['setprice'])
def setprice(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("price", msg.text.split(" ",1)[1])
    bot.reply_to(msg, "Done")

@bot.message_handler(commands=['setbuy'])
def setbuy(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("buy_link", msg.text.split(" ",1)[1])
    bot.reply_to(msg, "Done")

@bot.message_handler(commands=['addfolder'])
def addfolder(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    name = msg.text.split(" ",1)[1]
    add_folder(name)
    bot.reply_to(msg, "Folder added")

current_folder = None

@bot.message_handler(commands=['addvideo'])
def setfolder(msg):
    global current_folder
    if msg.from_user.id != ADMIN_ID:
        return

    current_folder = msg.text.split(" ",1)[1]
    bot.reply_to(msg, f"Send videos for {current_folder}")

@bot.message_handler(content_types=['video'])
def savevideo(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    add_video(current_folder, msg.video.file_id)
    bot.reply_to(msg, "Saved")

# -------- RUN --------
print("Bot running...")
bot.polling()
