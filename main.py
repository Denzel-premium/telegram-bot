import telebot
import random
import threading
import time

from config import TOKEN, ADMIN_ID
from db import *

bot = telebot.TeleBot(TOKEN)


# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):

    text = get_config("start_text", "👋 Welcome to Premium Bot")
    price = get_config("price", "29")
    link = get_config("buy_link", "https://google.com")

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📂 Video List")

    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton(f"💰 Buy ₹{price}", url=link))
    inline.add(telebot.types.InlineKeyboardButton("💳 I Have Paid", callback_data="paid"))

    bot.send_message(msg.chat.id, f"{text}\n💰 Price: ₹{price}", reply_markup=kb)
    bot.send_message(msg.chat.id, "👇 Buy Premium", reply_markup=inline)


# ================= PAID BUTTON =================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(call):
    bot.send_message(call.message.chat.id,
        "📸 Payment screenshot yaha bhejo"
    )


# ================= SCREENSHOT =================
@bot.message_handler(content_types=['photo'])
def ss(msg):

    add_pending(msg.from_user.id, msg.photo[-1].file_id)

    bot.send_message(msg.chat.id,
        "⏳ Screenshot received, wait for admin approval"
    )


# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin(msg):

    if int(msg.from_user.id) != int(ADMIN_ID):
        bot.send_message(msg.chat.id, "❌ Not allowed")
        return

    text = (
        "🛠 ADMIN PANEL\n\n"
        "✏️ /setstart - Set welcome message\n"
        "💰 /setprice - Set premium price\n"
        "🔗 /setbuy - Set payment URL\n"
        "📥 /requests - View payments\n"
    )

    bot.send_message(msg.chat.id, text)


# ================= SET START TEXT =================
@bot.message_handler(commands=['setstart'])
def setstart(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    set_config("start_text", msg.text.replace("/setstart ",""))
    bot.reply_to(msg, "✅ Start updated")


# ================= SET PRICE =================
@bot.message_handler(commands=['setprice'])
def setprice(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    set_config("price", msg.text.split(" ",1)[1])
    bot.reply_to(msg, "✅ Price updated")


# ================= SET BUY LINK =================
@bot.message_handler(commands=['setbuy'])
def setbuy(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    set_config("buy_link", msg.text.split(" ",1)[1])
    bot.reply_to(msg, "✅ Buy link updated")


# ================= REQUESTS =================
@bot.message_handler(commands=['requests'])
def requests(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    data = get_pending()

    for d in data:

        uid = d["user_id"]
        file_id = d["file_id"]

        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(
            telebot.types.InlineKeyboardButton("✅ Approve", callback_data=f"apv_{uid}"),
            telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}")
        )

        bot.send_photo(msg.chat.id, file_id,
            caption=f"User: {uid}",
            reply_markup=kb
        )


# ================= APPROVE =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("apv_"))
def approve(call):

    if call.from_user.id != ADMIN_ID:
        return

    uid = int(call.data.split("_")[1])

    key = "VIP1234"   # fixed key

    set_approved(uid, key)
    add_premium(uid)
    remove_pending(uid)

    bot.send_message(uid,
        f"🎉 Approved!\n🔑 Key: {key}\nUse /unlock {key}"
    )


# ================= REJECT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):

    if call.from_user.id != ADMIN_ID:
        return

    uid = int(call.data.split("_")[1])

    remove_pending(uid)
    bot.send_message(uid, "❌ Rejected")


# ================= UNLOCK =================
@bot.message_handler(commands=['unlock'])
def unlock(msg):

    parts = msg.text.split(" ",1)

    if len(parts) < 2:
        bot.reply_to(msg, "❌ /unlock KEY")
        return

    key = parts[1].strip()
    real = get_key(msg.from_user.id)

    if key == real:
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

    bot.send_message(msg.chat.id, "🎬 Access granted for 15 minutes")


# ================= AUTO EXPIRE =================
def auto_expire(user_id):
    time.sleep(900)
    temp_access.delete_one({"user_id": user_id})


# ================= RUN =================
print("Bot Running...")
bot.infinity_polling(skip_pending=True)
