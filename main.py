import telebot
import threading
import time
import urllib.parse
import random

from config import TOKEN, ADMIN_ID
from db import *

bot = telebot.TeleBot(TOKEN)

# ================= STORAGE =================
temp_access = {}
sent_videos = {}
current_folder = {}
admin_states = {}  # Admin state for image upload

channel_folder = "DEFAULT"


# ================= EXPIRY WORKER (25 MIN TIMER) =================
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
    # Save User ID for Broadcast System
    try:
        add_user(msg.from_user.id)
    except:
        pass

    text = get_config("start_text") or "👋 Welcome to Premium Bot"
    price = get_config("price") or "29"
    start_image = get_config("start_image")  # Dynamic Banner Image File ID

    # Main Reply Keyboard
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📥 Download")

    # Inline Buttons
    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton(f"💳 Buy via QR Code (₹{price})", callback_data="generate_qr"))
    inline.add(telebot.types.InlineKeyboardButton("📸 Upload Payment Screenshot", callback_data="paid"))

    caption_full = f"{text}\n\n💰 Price: ₹{price}"

    # Photo set hai to Photo bhejega, nahi to Text message
    if start_image:
        try:
            bot.send_photo(msg.chat.id, photo=start_image, caption=caption_full, reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, caption_full, reply_markup=kb)
    else:
        bot.send_message(msg.chat.id, caption_full, reply_markup=kb)

    bot.send_message(msg.chat.id, "👇 Click below to get Payment Details:", reply_markup=inline)


# ================= COLORFUL / DYNAMIC QR GENERATOR =================
@bot.callback_query_handler(func=lambda call: call.data == "generate_qr")
def generate_qr_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    price = get_config("price") or "29"
    upi_id = get_config("upi_id") or "example@upi"

    upi_url = f"upi://pay?pa={upi_id}&pn=PremiumBot&am={price}&cu=INR"

    # 🌈 Dynamic Bright / Neon QR Themes
    qr_themes = [
        {"color": "00f2fe", "bgcolor": "0f2027"},  # Neon Cyan
        {"color": "ff007f", "bgcolor": "1a1c23"},  # Neon Pink
        {"color": "00ff88", "bgcolor": "111827"},  # Emerald Green
        {"color": "ff9900", "bgcolor": "1c1917"},  # Vibrant Orange
        {"color": "a855f7", "bgcolor": "1e1b4b"},  # Purple Galaxy
    ]

    chosen_theme = random.choice(qr_themes)

    # API with Random Bright Colors
    qr_code_api = (
        f"https://api.qrserver.com/v1/create-qr-code/?"
        f"size=350x350&"
        f"bgcolor={chosen_theme['bgcolor']}&"
        f"color={chosen_theme['color']}&"
        f"data={urllib.parse.quote(upi_url)}"
    )

    # UPI Apps Direct Intents
    gpay_link = f"intent://pay?pa={upi_id}&pn=PremiumBot&am={price}&cu=INR#Intent;scheme=upi;package=com.google.android.apps.nbu.paisa.user;end"
    phonepe_link = f"intent://pay?pa={upi_id}&pn=PremiumBot&am={price}&cu=INR#Intent;scheme=upi;package=com.phonepe.app;end"
    paytm_link = f"intent://pay?pa={upi_id}&pn=PremiumBot&am={price}&cu=INR#Intent;scheme=upi;package=net.one97.paytm;end"

    redirect_kb = telebot.types.InlineKeyboardMarkup(row_width=2)
    redirect_kb.add(
        telebot.types.InlineKeyboardButton("🔵 Google Pay", url=gpay_link),
        telebot.types.InlineKeyboardButton("🟣 PhonePe", url=phonepe_link)
    )
    redirect_kb.add(
        telebot.types.InlineKeyboardButton("🟦 Paytm", url=paytm_link),
        telebot.types.InlineKeyboardButton("🔗 Any UPI App", url=upi_url)
    )

    caption_text = (
        f"✨ **OFFICIAL PAYMENT GATEWAY** ✨\n\n"
        f"📱 **SCAN & PAY ₹{price}**\n\n"
        f"📌 **UPI ID:** `{upi_id}` *(Tap to Copy)*\n"
        f"💰 **Amount:** ₹{price}\n\n"
        f"👇 Select UPI app or Scan QR Code, then send payment screenshot!"
    )

    try:
        bot.send_photo(
            call.message.chat.id, 
            photo=qr_code_api, 
            caption=caption_text, 
            parse_mode="Markdown", 
            reply_markup=redirect_kb
        )
    except Exception as e:
        bot.send_message(
            call.message.chat.id, 
            f"📌 **UPI ID:** `{upi_id}`\n💰 **Amount:** ₹{price}\n\nPay and send screenshot!", 
            parse_mode="Markdown",
            reply_markup=redirect_kb
        )


# ================= PAID SCREENSHOT REMINDER =================
@bot.callback_query_handler(func=lambda call: call.data == "paid")
def paid_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    bot.send_message(call.message.chat.id, "📸 Payment hone ke baad yahan **Screenshot** bhejo.")


# ================= CHANNEL AUTO SAVE =================
@bot.channel_post_handler(content_types=['video'])
def auto_save_channel(msg):
    add_video(channel_folder, msg.video.file_id)
    print(f"Saved in folder: {channel_folder}")


# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "❌ Not allowed")
        return

    text = (
        "🛠 **ADMIN PANEL**\n\n"
        "⚙️ **SETTINGS:**\n"
        "✏️ /setstart TEXT\n"
        "🖼 /setimage (Set Start Banner Photo)\n"
        "💰 /setprice PRICE\n"
        "💳 /setupi YOUR_UPI_ID\n"
        "🔗 /setbuy URL\n\n"
        "💳 /requests\n"
        "📢 /broadcast MESSAGE\n"
        "📊 /stats\n\n"
        "📂 /setfolder NAME\n"
        "📂 /setchannelfolder NAME\n"
        "📁 /folders\n"
        "🗑 /delfolder NAME\n"
        "❌ /delvideo INDEX\n"
    )

    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


# ================= SET IMAGE COMMAND =================
@bot.message_handler(commands=['setimage'])
def setimage_cmd(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    admin_states[msg.from_user.id] = "awaiting_start_image"
    bot.reply_to(msg, "📸 Abhi start banner ke liye **Image/Photo** bhejo:")


# ================= BROADCAST SYSTEM =================
@bot.message_handler(commands=['broadcast'])
def broadcast_msg(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    text = msg.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(msg, "❌ Usage: `/broadcast Your Message`", parse_mode="Markdown")
        return

    users = get_all_users()
    if not users:
        bot.reply_to(msg, "❌ No users found in database!")
        return

    success, failed = 0, 0
    bot.reply_to(msg, f"⏳ Broadcasting message to {len(users)} users...")

    for uid in users:
        try:
            bot.send_message(uid, text)
            success += 1
            time.sleep(0.05)
        except:
            failed += 1

    bot.send_message(msg.chat.id, f"✅ **Broadcast Completed!**\n\n🟢 Success: {success}\n🔴 Failed: {failed}", parse_mode="Markdown")


# ================= SET UPI ID =================
@bot.message_handler(commands=['setupi'])
def setupi(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(msg, "❌ Usage: `/setupi yourid@upi`", parse_mode="Markdown")
        return
    
    set_config("upi_id", parts[1].strip())
    bot.reply_to(msg, f"✅ UPI ID set to: `{parts[1].strip()}`", parse_mode="Markdown")


# ================= ADMIN STATS =================
@bot.message_handler(commands=['stats'])
def stats(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    folders_count = len(get_folders())
    users_count = len(get_all_users())
    bot.send_message(msg.chat.id, f"📊 **BOT STATS**\n\n👥 Total Users: {users_count}\n📂 Total Folders: {folders_count}", parse_mode="Markdown")


# ================= SETTINGS =================
@bot.message_handler(commands=['setchannelfolder'])
def set_channel_folder(msg):
    global channel_folder
    if msg.from_user.id != ADMIN_ID:
        return
    name = msg.text.replace("/setchannelfolder", "").strip()
    channel_folder = name
    bot.reply_to(msg, f"✅ Channel folder set: {name}")


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


# ================= PAYMENT & PHOTO HANDLER =================
@bot.message_handler(content_types=['photo'])
def handle_photos(msg):
    # Check if admin is setting start image
    if msg.from_user.id == ADMIN_ID and admin_states.get(ADMIN_ID) == "awaiting_start_image":
        file_id = msg.photo[-1].file_id
        set_config("start_image", file_id)
        admin_states[ADMIN_ID] = None
        bot.reply_to(msg, "✅ Start Banner Photo updated successfully!")
        return

    # Normal User Payment Screenshot
    add_pending(msg.from_user.id, msg.photo[-1].file_id)
    bot.send_message(msg.chat.id, "⏳ Wait for admin approval")


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


# ================= FOLDER MANAGEMENT =================
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
    text = "📂 **Folders List:**\n\n"
    for f in data:
        count = len(get_videos(f))
        text += f"👉 `{f}` ({count} videos)\n"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


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
    bot.reply_to(msg, f"🗑 Deleted folder: {name}")


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

    folders = get_folders()
    if not folders:
        bot.send_message(msg.chat.id, "❌ No folders available")
        return

    inline = telebot.types.InlineKeyboardMarkup()
    for f in folders:
        inline.add(telebot.types.InlineKeyboardButton(f"📂 {f}", callback_data=f"open_{f}"))

    bot.send_message(msg.chat.id, "📁 Select a folder to view content:", reply_markup=inline)


# ================= OPEN FOLDER & REGENERATE BUTTON =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("open_"))
def open_folder_cb(call):
    user_id = call.from_user.id

    if user_id not in temp_access:
        bot.send_message(call.message.chat.id, "❌ Click Download first")
        return

    folder = call.data.replace("open_", "").strip()
    vids = get_videos(folder)

    if not vids:
        bot.send_message(call.message.chat.id, "❌ No videos in this folder")
        return

    sent_videos[user_id] = []
    
    # Expiry Time set to 25 Minutes (1500 seconds)
    warning_caption = "⚠️ *This video will auto-delete in 25 minutes! Save or watch soon.*"

    for v in vids:
        m = bot.send_video(
            call.message.chat.id, 
            v["file_id"], 
            protect_content=True, 
            caption=warning_caption, 
            parse_mode="Markdown"
        )
        sent_videos[user_id].append(m.message_id)

    # Saved with 25 min (1500 seconds) lifetime
    set_expiry(
        user_id,
        sent_videos[user_id],
        call.message.chat.id,
        time.time() + 1500
    )

    # Regenerate / Fetch Again Inline Button
    refetch_kb = telebot.types.InlineKeyboardMarkup()
    refetch_kb.add(telebot.types.InlineKeyboardButton(f"🔄 Re-fetch '{folder}' Videos", callback_data=f"open_{folder}"))

    bot.send_message(
        call.message.chat.id, 
        f"⏳ **25 Minutes Timer Started!**\nIf videos are deleted before you finish, click below to load them again:", 
        reply_markup=refetch_kb,
        parse_mode="Markdown"
    )


# ================= RUN =================
print("Bot Running...")
bot.infinity_polling(skip_pending=True)
