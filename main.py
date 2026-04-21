import telebot
import threading
import time

from config import TOKEN, ADMIN_ID
from db import *

bot = telebot.TeleBot(TOKEN)

# ================= TEMP ACCESS =================
temp_access = {}   # user_id -> expiry
sent_videos = {}   # user_id -> message_ids


# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):

    text = get_config("start_text") or "👋 Welcome"
    price = get_config("price") or "29"
    link = get_config("buy_link") or "https://google.com"

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📥 Download")

    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton(f"💰 Buy ₹{price}", url=link))
    inline.add(telebot.types.InlineKeyboardButton("💳 I Have Paid", callback_data="paid"))

    bot.send_message(msg.chat.id, f"{text}\n💰 Price: ₹{price}", reply_markup=kb)
    bot.send_message(msg.chat.id, "👇 Buy Premium", reply_markup=inline)


# ================= PAID =================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(call):
    bot.send_message(call.message.chat.id, "📸 Payment screenshot bhejo")


# ================= SCREENSHOT =================
@bot.message_handler(content_types=['photo'])
def ss(msg):
    add_pending(msg.from_user.id, msg.photo[-1].file_id)
    bot.send_message(msg.chat.id, "⏳ Screenshot received, wait for admin")


# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin(msg):

    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "❌ Not allowed")
        return

    text = (
        "🛠 ADMIN PANEL\n\n"
        "✏️ /setstart - Set welcome\n"
        "💰 /setprice - Set price\n"
        "🔗 /setbuy - Set payment link\n"
        "📥 /requests - View payments\n"
        "📂 /folders - View folders\n"
        "➕ /addvideo - Add video (file_id)\n\n"
        "📌 Steps:\n"
        "1. Bot me video bhejo → file_id milega\n"
        "2. /addvideo FOLDER FILE_ID"
    )

    bot.send_message(msg.chat.id, text)


# ================= SETTINGS =================
@bot.message_handler(commands=['setstart'])
def setstart(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("start_text", msg.text.replace("/setstart ", ""))
    bot.reply_to(msg, "✅ Updated")


@bot.message_handler(commands=['setprice'])
def setprice(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("price", msg.text.split(" ", 1)[1])
    bot.reply_to(msg, "✅ Updated")


@bot.message_handler(commands=['setbuy'])
def setbuy(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    url = msg.text.split(" ", 1)[1]
    set_config("buy_link", url)
    bot.reply_to(msg, "✅ Updated")


# ================= REQUESTS =================
@bot.message_handler(commands=['requests'])
def requests(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    for d in get_pending():

        uid = d["user_id"]

        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(
            telebot.types.InlineKeyboardButton("✅ Approve", callback_data=f"apv_{uid}"),
            telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}")
        )

        bot.send_photo(msg.chat.id, d["file_id"], caption=f"User: {uid}", reply_markup=kb)


# ================= APPROVE =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("apv_"))
def approve(call):

    uid = int(call.data.split("_")[1])

    add_premium(uid)
    remove_pending(uid)

    bot.send_message(uid, "🎉 Approved!\n📥 Click Download")


# ================= REJECT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):

    uid = int(call.data.split("_")[1])
    remove_pending(uid)
    bot.send_message(uid, "❌ Rejected")


# ================= GET FILE ID =================
@bot.message_handler(content_types=['video'])
def get_file_id(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    bot.reply_to(msg, f"📌 FILE ID:\n{msg.video.file_id}")


# ================= ADD VIDEO =================
@bot.message_handler(commands=['addvideo'])
def addvideo(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    parts = msg.text.split(" ")

    if len(parts) < 3:
        bot.reply_to(msg, "❌ Use:\n/addvideo FOLDER FILE_ID")
        return

    folder = parts[1]
    file_id = parts[2]

    add_video(folder, file_id)

    bot.reply_to(msg, f"✅ Added to {folder}")


# ================= SHOW FOLDERS =================
@bot.message_handler(commands=['folders'])
def showfolders(msg):

    data = get_folders()

    text = "📂 Folders:\n\n"
    for f in data:
        text += f"👉 {f}\n"

    bot.send_message(msg.chat.id, text)


# ================= AUTO EXPIRE =================
def auto_expire(user_id):

    time.sleep(900)

    temp_access.pop(user_id, None)

    if user_id in sent_videos:
        for mid in sent_videos[user_id]:
            try:
                bot.delete_message(user_id, mid)
            except:
                pass
        sent_videos.pop(user_id, None)


# ================= DOWNLOAD =================
@bot.message_handler(func=lambda m: m.text == "📥 Download")
def download(msg):

    user_id = msg.from_user.id

    if not is_premium(user_id):
        bot.send_message(msg.chat.id, "❌ Premium required")
        return

    # ✅ spam fix
    if user_id not in temp_access:
        temp_access[user_id] = time.time() + 900
        threading.Thread(target=auto_expire, args=(user_id,), daemon=True).start()

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    folders = get_folders()

    if not folders:
        bot.send_message(msg.chat.id, "❌ No folders available")
        return

    for f in folders:
        kb.add(f"📂 {f}")

    bot.send_message(msg.chat.id, "⏳ 15 min access", reply_markup=kb)


# ================= OPEN FOLDER =================
@bot.message_handler(func=lambda m: m.text.startswith("📂 "))
def open_folder(msg):

    user_id = msg.from_user.id

    if user_id not in temp_access or time.time() > temp_access[user_id]:
        bot.send_message(msg.chat.id, "❌ Access expired\n👉 Click Download again")
        return

    folder = msg.text.replace("📂 ", "").strip()

    vids = get_videos(folder)

    # ✅ empty folder fix
    if not vids:
        bot.send_message(msg.chat.id, "❌ No videos in this folder")
        return

    sent_videos.setdefault(user_id, [])

    for v in vids:
        m = bot.send_video(
            msg.chat.id,
            v["file_id"],
            protect_content=True
        )
        sent_videos[user_id].append(m.message_id)


# ================= RUN =================
print("Bot Running...")
bot.infinity_polling(skip_pending=True)
