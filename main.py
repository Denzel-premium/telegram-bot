import telebot
import threading
import time

from config import TOKEN, ADMIN_ID
from db import *

bot = telebot.TeleBot(TOKEN)

# ================= STORAGE =================
temp_access = {}
sent_videos = {}
current_folder = {}

channel_folder = "DEFAULT"


# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):

    text = get_config("start_text") or "👋 Welcome"
    price = get_config("price") or "29"
    link = get_config("buy_link") or "https://google.com"

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📥 Download")

    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(
        telebot.types.InlineKeyboardButton(f"💰 Buy ₹{price}", url=link)
    )
    inline.add(
        telebot.types.InlineKeyboardButton("💳 I Have Paid", callback_data="paid")
    )

    bot.send_message(msg.chat.id, f"{text}\n💰 Price: ₹{price}", reply_markup=kb)
    bot.send_message(msg.chat.id, "👇 Buy Premium", reply_markup=inline)


# ================= PAID BUTTON =================
@bot.callback_query_handler(func=lambda call: call.data == "paid")
def paid_handler(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📸 Payment screenshot bhejo")


# ================= CHANNEL AUTO SAVE =================
@bot.channel_post_handler(content_types=['video'])
def auto_save_channel(msg):
    add_video(channel_folder, msg.video.file_id)


# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin(msg):

    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "❌ Not allowed")
        return

    text = (
        "🛠 ADMIN PANEL\n\n"

        "⚙️ SETTINGS:\n"
        "✏️ /setstart\n"
        "💰 /setprice\n"
        "🔗 /setbuy\n\n"

        "💳 PAYMENTS:\n"
        "📥 /requests\n\n"

        "📂 VIDEO MANAGEMENT:\n"
        "📂 /setfolder\n"
        "📂 /setchannelfolder\n"
        "👁 /viewfolder NAME\n"
        "📁 /folders\n"
        "🗑 /delfolder\n"
        "❌ /delvideo\n"
    )

    bot.send_message(msg.chat.id, text)


# ================= VIEW FOLDER (NEW) =================
@bot.message_handler(commands=['viewfolder'])
def view_folder(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    name = msg.text.replace("/viewfolder", "").strip()

    if not name:
        bot.reply_to(msg, "❌ Use /viewfolder NAME")
        return

    vids = get_videos(name)

    if not vids:
        bot.send_message(msg.chat.id, "❌ No videos found")
        return

    text = f"📂 {name}\nTotal Videos: {len(vids)}\n\n"

    for i, v in enumerate(vids):
        text += f"{i} ➜ {v['file_id'][:30]}...\n"

    bot.send_message(msg.chat.id, text)


# ================= DOWNLOAD =================
@bot.message_handler(func=lambda m: m.text == "📥 Download")
def download(msg):

    if not is_premium(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Premium required")
        return

    user_id = msg.from_user.id
    temp_access[user_id] = True

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    for f in get_folders():
        kb.add(f"📂 {f}")

    bot.send_message(msg.chat.id, "⏳ Select Folder", reply_markup=kb)


# ================= OPEN FOLDER =================
@bot.message_handler(func=lambda m: m.text.startswith("📂 "))
def open_folder(msg):

    user_id = msg.from_user.id

    if user_id not in temp_access:
        bot.send_message(msg.chat.id, "❌ Click Download first")
        return

    folder = msg.text.replace("📂 ", "").strip()

    vids = get_videos(folder)

    sent_videos[user_id] = []

    for v in vids:
        m = bot.send_video(msg.chat.id, v["file_id"], protect_content=True)
        sent_videos[user_id].append(m.message_id)

    threading.Thread(target=auto_expire, args=(user_id,), daemon=True).start()


# ================= AUTO DELETE ONLY =================
def auto_expire(user_id):

    time.sleep(900)

    if user_id in sent_videos:
        for mid in sent_videos[user_id]:
            try:
                bot.delete_message(user_id, mid)
            except:
                pass

        sent_videos.pop(user_id, None)


# ================= RUN =================
print("Bot Running...")
bot.infinity_polling(skip_pending=True)
