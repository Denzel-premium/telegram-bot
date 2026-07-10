import telebot
import threading
import time   # ✅ FIX ADD

from config import TOKEN, ADMIN_ID
from db import *

bot = telebot.TeleBot(TOKEN)

# ================= STORAGE =================
temp_access = {}
sent_videos = {}
current_folder = {}

channel_folder = "DEFAULT"


# ================= EXPIRY WORKER (✅ ADD ONLY) =================
def expiry_worker():
    while True:
        try:
            now = time.time()

            expired = get_expired(now)

            for item in expired:
                chat_id = item["chat_id"]

                for mid in item["message_ids"]:
                    try:
                        bot.delete_message(chat_id, mid)
                    except:
                        pass

                delete_expiry(item["_id"])

        except Exception as e:
            print("Expiry error:", e)

        time.sleep(30)


threading.Thread(target=expiry_worker, daemon=True).start()


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


# ================= PAID BUTTON =================
@bot.callback_query_handler(func=lambda call: call.data == "paid")
def paid_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    bot.send_message(call.message.chat.id, "📸 Payment screenshot bhejo")


# ================= CHANNEL AUTO SAVE =================
@bot.channel_post_handler(content_types=['video'])
def auto_save_channel(msg):
    add_video(channel_folder, msg.video.file_id)
    print(f"Saved in folder: {channel_folder}")


# ================= ADMIN PANEL (UNCHANGED) =================
@bot.message_handler(commands=['admin'])
def admin(msg):

    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "❌ Not allowed")
        return

    text = (
        "🛠 ADMIN PANEL\n\n"
        "⚙️ SETTINGS:\n"
        "✏️ /setstart TEXT\n"
        "💰 /setprice PRICE\n"
        "🔗 /setbuy URL\n\n"
        "💳 /requests\n\n"
        "📂 /setfolder NAME\n"
        "📂 /setchannelfolder NAME\n"
        "📁 /folders\n"
        "🗑 /delfolder NAME\n"
        "❌ /delvideo INDEX\n"
    )

    bot.send_message(msg.chat.id, text)


# ================= SET CHANNEL FOLDER =================
@bot.message_handler(commands=['setchannelfolder'])
def set_channel_folder(msg):

    global channel_folder

    if msg.from_user.id != ADMIN_ID:
        return

    name = msg.text.replace("/setchannelfolder", "").strip()
    channel_folder = name
    bot.reply_to(msg, f"✅ Channel folder set: {name}")


# ================= SETTINGS =================
@bot.message_handler(commands=['setstart'])
def setstart(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("start_text", msg.text.replace("/setstart ", ""))


@bot.message_handler(commands=['setprice'])
def setprice(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("price", msg.text.split(" ", 1)[1])


@bot.message_handler(commands=['setbuy'])
def setbuy(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("buy_link", msg.text.split(" ", 1)[1])


# ================= PAYMENT =================
@bot.message_handler(content_types=['photo'])
def ss(msg):
    add_pending(msg.from_user.id, msg.photo[-1].file_id)
    bot.send_message(msg.chat.id, "⏳ Wait for approval")


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


@bot.callback_query_handler(func=lambda c: c.data.startswith("apv_"))
def approve(call):
    uid = int(call.data.split("_")[1])
    add_premium(uid)
    remove_pending(uid)
    bot.send_message(uid, "🎉 Approved!\n📥 Click Download")


@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):
    uid = int(call.data.split("_")[1])
    remove_pending(uid)
    bot.send_message(uid, "❌ Rejected")


# ================= FOLDER =================
@bot.message_handler(commands=['setfolder'])
def setfolder(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    name = msg.text.replace("/setfolder", "").strip()

    if not name:
        bot.reply_to(msg, "❌ Use /setfolder NAME")
        return

    current_folder[msg.from_user.id] = name
    bot.reply_to(msg, f"📂 Active folder: {name}")


@bot.message_handler(commands=['folders'])
def showfolders(msg):

    data = get_folders()

    text = "📂 Folders:\n\n"

    for f in data:
        count = len(get_videos(f))
        text += f"👉 {f} ({count})\n"

    bot.send_message(msg.chat.id, text)


# ================= SAVE VIDEO =================
@bot.message_handler(content_types=['video'])
def savevideo(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    if msg.from_user.id not in current_folder:
        bot.reply_to(msg, "❌ Use /setfolder first")
        return

    folder = current_folder[msg.from_user.id]

    add_video(folder, msg.video.file_id)

    bot.reply_to(msg, f"✅ Saved in {folder}")


# ================= DELETE =================
@bot.message_handler(commands=['delfolder'])
def delfolder(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    name = msg.text.replace("/delfolder", "").strip()

    delete_folder(name)

    bot.reply_to(msg, f"🗑 Deleted {name}")


@bot.message_handler(commands=['delvideo'])
def delvideo(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    parts = msg.text.split(" ")

    if len(parts) < 2:
        bot.reply_to(msg, "❌ /delvideo INDEX")
        return

    index = int(parts[1])

    if msg.from_user.id not in current_folder:
        bot.reply_to(msg, "❌ Set folder first")
        return

    folder = current_folder[msg.from_user.id]

    delete_video(folder, index)

    bot.reply_to(msg, "❌ Video deleted")


# ================= DOWNLOAD =================
@bot.message_handler(func=lambda m: m.text == "📥 Download")
def download(msg):

    if not is_premium(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Premium required")
        return

    user_id = msg.from_user.id

    temp_access[user_id] = True

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    folders = get_folders()

    if not folders:
        bot.send_message(msg.chat.id, "❌ No folders")
        return

    for f in folders:
        kb.add(f"📂 {f}")

    bot.send_message(msg.chat.id, "⏳ Videos ready (auto delete in 15 min)", reply_markup=kb)


# ================= OPEN =================
@bot.message_handler(func=lambda m: m.text.startswith("📂 "))
def open_folder(msg):

    user_id = msg.from_user.id

    if user_id not in temp_access:
        bot.send_message(msg.chat.id, "❌ Click Download first")
        return

    folder = msg.text.replace("📂 ", "").strip()

    vids = get_videos(folder)

    if not vids:
        bot.send_message(msg.chat.id, "❌ No videos")
        return

    sent_videos[user_id] = []

    for v in vids:
        m = bot.send_video(msg.chat.id, v["file_id"], protect_content=True)

        # ❗ FIX ONLY (store message_id only)
        sent_videos[user_id].append(m.message_id)

    # ✅ DB EXPIRY SAVE ADD
    set_expiry(
        user_id,
        sent_videos[user_id],
        msg.chat.id,
        time.time() + 900
    )


# ================= RUN =================
print("Bot Running...")
bot.infinity_polling(skip_pending=True)
