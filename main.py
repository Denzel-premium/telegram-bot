import telebot
import random
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

    bot.send_message(msg.chat.id, "👋 Welcome", reply_markup=kb)
    bot.send_message(msg.chat.id, "👇 Buy Premium:", reply_markup=inline)


# ================= BUY =================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(call):

    bot.send_message(call.message.chat.id,
        "💳 Payment karo aur screenshot yaha bhejo 📸"
    )


# ================= SCREENSHOT STORE =================
@bot.message_handler(content_types=['photo'])
def ss(msg):

    pending_users[msg.from_user.id] = msg.photo[-1].file_id

    bot.send_message(msg.chat.id,
        "⏳ Screenshot received. Waiting for admin approval..."
    )


# ================= ADMIN PANEL =================
@bot.message_handler(commands=['requests'])
def requests(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    if not pending_users:
        bot.send_message(msg.chat.id, "No pending requests")
        return

    for uid, file_id in pending_users.items():

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"apv_{uid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}")
        )

        bot.send_photo(msg.chat.id, file_id,
            caption=f"User ID: {uid}",
            reply_markup=kb
        )


# ================= APPROVE / REJECT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("apv_"))
def approve(call):

    if call.from_user.id != ADMIN_ID:
        return

    uid = int(call.data.split("_")[1])

    key = "PREM" + str(random.randint(1000,9999))

    approved_users[uid] = key
    premium_users.add(uid)

    pending_users.pop(uid, None)

    bot.send_message(uid,
        f"🎉 Approved!\n🔑 Your Key: {key}\nUse /unlock {key}"
    )

    bot.answer_callback_query(call.id, "Approved")


@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):

    if call.from_user.id != ADMIN_ID:
        return

    uid = int(call.data.split("_")[1])

    pending_users.pop(uid, None)

    bot.send_message(uid, "❌ Request Rejected")

    bot.answer_callback_query(call.id, "Rejected")


# ================= UNLOCK =================
@bot.message_handler(commands=['unlock'])
def unlock(msg):

    parts = msg.text.split(" ",1)

    if len(parts) < 2:
        bot.reply_to(msg, "❌ /unlock KEY")
        return

    key = parts[1]

    if approved_users.get(msg.from_user.id) == key:
        premium_users.add(msg.from_user.id)
        bot.reply_to(msg, "✅ Premium Activated!")
    else:
        bot.reply_to(msg, "❌ Invalid Key")


# ================= VIDEO =================
@bot.message_handler(func=lambda m: m.text == "📂 Video List")
def videos(msg):

    if msg.from_user.id not in premium_users:
        bot.send_message(msg.chat.id, "❌ Premium required")
        return

    bot.send_message(msg.chat.id, "🎬 Videos unlocked")


# ================= ADMIN REQUEST VIEW =================
@bot.message_handler(commands=['admin'])
def admin(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    bot.send_message(msg.chat.id,
        "/requests - view payments\n/approve system buttons"
    )


# ================= RUN =================
print("Bot Running...")
bot.polling()
