import telebot
import random
import threading
import time
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from config import TOKEN, ADMIN_ID
from db import *

bot = telebot.TeleBot(TOKEN)


# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📂 Video List")

    inline = InlineKeyboardMarkup()
    inline.add(InlineKeyboardButton("💰 Buy Premium", callback_data="buy"))

    bot.send_message(msg.chat.id, "👋 Welcome to Premium Bot", reply_markup=kb)
    bot.send_message(msg.chat.id, "👇 Buy Premium:", reply_markup=inline)


# ================= BUY =================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(call):

    bot.send_message(call.message.chat.id,
        "💳 Payment karo aur screenshot yaha bhejo 📸"
    )


# ================= SCREENSHOT =================
@bot.message_handler(content_types=['photo'])
def ss(msg):

    add_pending(msg.from_user.id, msg.photo[-1].file_id)

    bot.send_message(msg.chat.id,
        "⏳ Screenshot received. Wait for admin approval..."
    )


# ================= ADMIN REQUESTS =================
@bot.message_handler(commands=['requests'])
def requests(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    data = get_pending()

    if not data:
        bot.send_message(msg.chat.id, "No pending requests")
        return

    for d in data:

        uid = d["user_id"]
        file_id = d["file_id"]

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"apv_{uid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}")
        )

        bot.send_photo(msg.chat.id, file_id,
            caption=f"User ID: {uid}",
            reply_markup=kb
        )


# ================= APPROVE =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("apv_"))
def approve(call):

    if call.from_user.id != ADMIN_ID:
        return

    uid = int(call.data.split("_")[1])

    key = "PREM" + str(random.randint(1000,9999))

    set_approved(uid, key)
    add_premium(uid)
    remove_pending(uid)

    bot.send_message(uid,
        f"🎉 Approved!\n🔑 Key: {key}\nUse /unlock {key}"
    )

    bot.answer_callback_query(call.id, "Approved")


# ================= REJECT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):

    if call.from_user.id != ADMIN_ID:
        return

    uid = int(call.data.split("_")[1])

    remove_pending(uid)

    bot.send_message(uid, "❌ Rejected")
    bot.answer_callback_query(call.id, "Rejected")


# ================= UNLOCK =================
@bot.message_handler(commands=['unlock'])
def unlock(msg):

    parts = msg.text.split(" ",1)

    if len(parts) < 2:
        bot.reply_to(msg, "❌ /unlock KEY")
        return

    key = parts[1].strip()
    real_key = get_key(msg.from_user.id)

    if key == real_key:
        add_premium(msg.from_user.id)
        bot.reply_to(msg, "✅ Premium Activated!")
    else:
        bot.reply_to(msg, "❌ Invalid Key")


# ================= VIDEO LIST =================
@bot.message_handler(func=lambda m: m.text == "📂 Video List")
def videos(msg):

    if not is_premium(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Premium required")
        return

    give_temp_access(msg.from_user.id)

    threading.Thread(target=auto_expire, args=(msg.from_user.id,)).start()

    bot.send_message(msg.chat.id, "🎬 Access granted for 15 minutes ⏳")


# ================= TEMP EXPIRE =================
def auto_expire(user_id):
    time.sleep(900)  # 15 min
    temp_access.delete_one({"user_id": user_id})


# ================= CHECK ACCESS FUNCTION =================
def can_access(user_id):
    data = temp_access.find_one({"user_id": user_id})

    if not data:
        return False

    return (time.time() - data["start_time"]) <= 900


# ================= VIDEO SEND (PLACEHOLDER) =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("folder_"))
def send_videos(call):

    if not can_access(call.from_user.id):
        bot.answer_callback_query(call.id, "⏳ Access expired")
        return

    bot.send_message(call.message.chat.id, "🎬 Here are your videos")


# ================= RUN =================
print("Bot Running...")
bot.polling()
