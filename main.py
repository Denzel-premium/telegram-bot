import telebot
import random
import threading
import time

from config import TOKEN, ADMIN_ID
from db import *

bot = telebot.TeleBot(TOKEN)

# ================= FOLDER SYSTEM STORAGE =================
folders = {}          # folder_name -> [video_file_ids]
pending_folder = {}   # admin upload tracking
upload_mode = {}      # admin_id -> folder (MULTI UPLOAD MODE)

# ================= NEW: TEMP ACCESS SYSTEM =================
temp_access = {}  # user_id -> expiry timestamp


# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):

    text = get_config("start_text") or "👋 Welcome"
    price = get_config("price") or "29"

    upi_id = get_config("upi_id")
    if not upi_id:
        upi_id = "yourupi@okaxis"

    link = f"upi://pay?pa={upi_id}&pn=Premium&am={price}&cu=INR"

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📂 Video List", "📥 Download")

    inline = telebot.types.InlineKeyboardMarkup()

    btn1 = telebot.types.InlineKeyboardButton(
        f"💰 Buy ₹{price}", url=link
    )

    btn2 = telebot.types.InlineKeyboardButton(
        "💳 I Have Paid", callback_data="paid"
    )

    inline.add(btn1)
    inline.add(btn2)

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


# ================= ADMIN PANEL (UNCHANGED) =================
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
        "📁 /addfolder - Create Folder\n"
        "📤 /upload - Upload Videos (multi mode)\n"
        "🛑 /stopupload - Stop upload mode\n"
        "📂 /folders - View Folders\n"
        "▶️ /open - Open Folder Videos\n"
        "🗑 /delfolder - Delete Folder\n"
    )

    bot.send_message(msg.chat.id, text)


# ================= SET COMMANDS =================
@bot.message_handler(commands=['setstart'])
def setstart(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("start_text", msg.text.replace("/setstart ",""))
    bot.reply_to(msg, "✅ Start updated")


@bot.message_handler(commands=['setprice'])
def setprice(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    set_config("price", msg.text.split(" ",1)[1])
    bot.reply_to(msg, "✅ Price updated")


@bot.message_handler(commands=['setbuy'])
def setbuy(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    upi = msg.text.split(" ",1)[1].strip()

    set_config("upi_id", upi)

    bot.reply_to(msg, "✅ UPI ID updated")


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

    uid = int(call.data.split("_")[1])

    # 🔥 direct premium activate (NO KEY)
    add_premium(uid)
    remove_pending(uid)

    bot.send_message(uid,
        "🎉 Approved!\n🔥 Premium Activated Successfully\n📂 Now open Video List"
    )


# ================= REJECT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):

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
    temp_access.pop(user_id, None)


# ================= FOLDER SYSTEM =================
@bot.message_handler(commands=['addfolder'])
def addfolder(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    name = msg.text.replace("/addfolder", "").strip()

    if not name:
        bot.reply_to(msg, "❌ Folder name required\nExample: /addfolder VIP")
        return

    folders[name] = []

    bot.reply_to(msg, f"📁 Folder '{name}' created")


@bot.message_handler(commands=['folders'])
def showfolders(msg):

    text = "📂 Folders:\n\n"
    for f in folders:
        text += f"👉 {f}\n"

    bot.send_message(msg.chat.id, text)


@bot.message_handler(commands=['open'])
def openfolder(msg):

    name = msg.text.replace("/open", "").strip()

    for v in folders.get(name, []):
        bot.send_video(msg.chat.id, v)

@bot.message_handler(commands=['delfolder'])
def delfolder(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    name = msg.text.replace("/delfolder", "").strip()

    if not name:
        bot.reply_to(msg, "❌ Use /delfolder FOLDER_NAME")
        return

    if name in folders:
        folders.pop(name)
        bot.reply_to(msg, f"🗑 Folder '{name}' deleted")
    else:
        bot.reply_to(msg, "❌ Folder not found")


# ================= MULTI UPLOAD =================
@bot.message_handler(commands=['upload'])
def upload(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    name = msg.text.replace("/upload", "").strip()
    upload_mode[msg.from_user.id] = name

    bot.reply_to(msg, "📤 Upload ON")


@bot.message_handler(commands=['stopupload'])
def stopupload(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    upload_mode.pop(msg.from_user.id, None)

    bot.reply_to(msg, "🛑 Upload OFF")


@bot.message_handler(content_types=['video'])
def savevideo(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    uid = msg.from_user.id

    if uid not in upload_mode:
        return

    folder = upload_mode[uid]

    folders.setdefault(folder, []).append(msg.video.file_id)

    bot.send_message(msg.chat.id, f"✅ Added to {folder}")


# ================= 📥 DOWNLOAD (NEW FEATURE) =================
@bot.message_handler(func=lambda m: m.text == "📥 Download")
def download_menu(msg):

    user_id = msg.from_user.id

    if not is_premium(user_id):
        bot.send_message(msg.chat.id, "❌ Premium required")
        return

    temp_access[user_id] = time.time() + 900  # 15 min

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    text = "📥 Select Folder:\n\n"
    for f in folders:
        text += f"👉 {f}\n"
        kb.add(f"📂 {f}")

    bot.send_message(msg.chat.id,
        "⏳ 15 min access granted\n\n" + text,
        reply_markup=kb
    )


# ================= 📂 OPEN WITH ACCESS CHECK =================
@bot.message_handler(func=lambda m: m.text.startswith("📂 "))
def open_from_menu(msg):

    user_id = msg.from_user.id

    if user_id not in temp_access or time.time() > temp_access[user_id]:
        bot.send_message(msg.chat.id,
            "❌ Access expired\n👉 Click 📥 Download again"
        )
        return

    name = msg.text.replace("📂 ", "").strip()

    if name not in folders:
        bot.send_message(msg.chat.id, "❌ Not found")
        return

    for v in folders[name]:
        bot.send_video(msg.chat.id, v)


# ================= RUN =================
print("Bot Running...")
bot.infinity_polling(skip_pending=True)
