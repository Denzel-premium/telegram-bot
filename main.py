import io
import threading
import time
import urllib.parse
import requests
import telebot

from config import ADMIN_ID, TOKEN
from db import *

bot = telebot.TeleBot(TOKEN)

# ================= STORAGE =================
temp_access = {}
sent_videos = {}
current_folder = {}
admin_states = {}
user_pending_folder = {}
all_user_ids = set()

channel_folder = "DEFAULT"


# ================= HELPER FUNCTIONS =================
def is_admin(user_id):
    if not ADMIN_ID:
        return False
    return str(user_id).strip() == str(ADMIN_ID).strip()


def track_user(user_id):
    all_user_ids.add(user_id)
    try:
        add_user(user_id)
    except Exception:
        pass


# ================= MAIN MENU BUILDER =================
def build_main_menu():
    text = get_config("start_text") or "👋 Welcome"
    price = get_config("price") or "29"

    inline = telebot.types.InlineKeyboardMarkup(row_width=1)
    inline.add(
        telebot.types.InlineKeyboardButton(f"💰 Buy Premium ₹{price}", callback_data="generate_qr"),
        telebot.types.InlineKeyboardButton("👁️ Demo", callback_data="show_demo"),
        telebot.types.InlineKeyboardButton("💳 I Have Paid", callback_data="paid_main"),
        telebot.types.InlineKeyboardButton("📂 Folder Passes", callback_data="folder_pass_menu"),
    )
    return text, inline


# ================= EXPIRY WORKER =================
def expiry_worker():
    while True:
        try:
            now = time.time()
            expired = get_expired(now)

            if expired:
                for item in expired:
                    chat_id = item["chat_id"]
                    for mid in item.get("message_ids", []):
                        try:
                            bot.delete_message(chat_id, mid)
                        except Exception:
                            pass
                    delete_expiry(item["_id"])

        except Exception as e:
            print("Expiry error:", e)

        time.sleep(15)


threading.Thread(target=expiry_worker, daemon=True).start()


# ================= START COMMAND =================
@bot.message_handler(commands=['start'])
def start(msg):
    track_user(msg.from_user.id)

    text, inline = build_main_menu()
    start_image = get_config("start_image")

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📥 Download")

    if start_image:
        try:
            bot.send_photo(msg.chat.id, photo=start_image, caption=text, reply_markup=kb)
        except Exception:
            bot.send_message(msg.chat.id, text, reply_markup=kb)
    else:
        bot.send_message(msg.chat.id, text, reply_markup=kb)

    bot.send_message(msg.chat.id, "👇 Select Option Below:", reply_markup=inline, parse_mode="Markdown")


# ================= NAVIGATION =================
@bot.callback_query_handler(func=lambda call: call.data == "go_home")
def go_home_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    text, inline = build_main_menu()

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot.send_message(call.message.chat.id, text, reply_markup=inline, parse_mode="Markdown")


# ================= BUY PREMIUM =================
@bot.callback_query_handler(func=lambda call: call.data == "generate_qr")
def generate_qr_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    price = get_config("price") or "29"
    upi_id = get_config("upi_id") or "example@upi"
    upi_url = f"upi://pay?pa={upi_id}&pn=Premium&am={price}&cu=INR"

    user_pending_folder[call.from_user.id] = "ONLINE_VIP_PLAN"

    inline = telebot.types.InlineKeyboardMarkup(row_width=1)
    inline.add(
        telebot.types.InlineKeyboardButton("💳 I Have Paid", callback_data="paid_main"),
        telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
    )

    caption_text = (
        f"👑 **BUY PREMIUM ₹{price}** 👑\n\n"
        f"📱 **SCAN & PAY ₹{price}**\n\n"
        f"📌 **UPI ID:** `{upi_id}` *(Tap to copy)*\n"
        f"💰 **Amount:** ₹{price}\n\n"
        f"👉 Payment karne ke baad [ 💳 I Have Paid ] button par click karke screenshot bhej dein!"
    )

    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&margin=10&bgcolor=ffffff&color=000000&data={urllib.parse.quote(upi_url)}"

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    try:
        bot.send_photo(call.message.chat.id, photo=qr_api, caption=caption_text, reply_markup=inline, parse_mode="Markdown")
    except Exception:
        bot.send_message(call.message.chat.id, caption_text, reply_markup=inline, parse_mode="Markdown")


# ================= DEMO =================
@bot.callback_query_handler(func=lambda call: call.data == "show_demo")
def show_demo_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    user_id = call.from_user.id
    chat_id = call.message.chat.id

    demo_file = get_config("demo_file_id")
    demo_type = get_config("demo_type")
    demo_text = get_config("demo_text") or "👁️ Here is Demo Content!"

    if not demo_file and not demo_text:
        bot.answer_callback_query(call.id, "❌ Demo content available nahi hai.", show_alert=True)
        return

    buy_kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    price = get_config("price") or "29"
    buy_kb.add(
        telebot.types.InlineKeyboardButton(f"💰 Buy Premium ₹{price}", callback_data="generate_qr"),
        telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
    )

    sent_demo_ids = []
    demo_caption = f"{demo_text}\n\n⚠️ Yeh demo 10 minute me delete ho jayega!"

    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass

    if demo_type == "video" and demo_file:
        m1 = bot.send_video(chat_id, video=demo_file, caption=demo_caption, reply_markup=buy_kb, protect_content=True)
        sent_demo_ids.append(m1.message_id)
    elif demo_type == "photo" and demo_file:
        m1 = bot.send_photo(chat_id, photo=demo_file, caption=demo_caption, reply_markup=buy_kb)
        sent_demo_ids.append(m1.message_id)
    else:
        m1 = bot.send_message(chat_id, demo_caption, reply_markup=buy_kb)
        sent_demo_ids.append(m1.message_id)

    if sent_demo_ids:
        set_expiry(user_id, sent_demo_ids, chat_id, time.time() + 600)


# ================= I HAVE PAID BUTTON =================
@bot.callback_query_handler(func=lambda call: call.data == "paid_main")
def paid_main_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    user_pending_folder[call.from_user.id] = "ONLINE_VIP_PLAN"

    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))

    text = (
        f"📸 **PAYMENT SCREENSHOT BHEJEIN** 📸\n\n"
        f"👉 Payment ka Screenshot abhi chat me bhej dein! Admin verify karke access de dega."
    )

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot.send_message(call.message.chat.id, text, reply_markup=inline, parse_mode="Markdown")


# ================= FOLDER PASSES MENU =================
@bot.callback_query_handler(func=lambda call: call.data == "folder_pass_menu")
def folder_pass_menu(call):
    user_id = call.from_user.id
    folders = get_folders() or []
    if not folders:
        bot.answer_callback_query(call.id, "❌ No folders available", show_alert=True)
        return

    default_text = "📁 **FOLDER PASSES**\n\nNiche se folder select karke pass buy karein:"
    pass_instruction = get_config("pass_text") or default_text

    inline = telebot.types.InlineKeyboardMarkup(row_width=1)
    for f in folders:
        f_price = get_config(f"folder_price_{f}") or "49"
        vids = get_videos(f) or []
        v_count = len(vids)
        
        is_unlocked = has_folder_access_db(user_id, f)

        if is_unlocked:
            status_text = " ✅ Unlocked"
        else:
            status_text = f" 🔒 • ₹{f_price}"
            
        inline.add(telebot.types.InlineKeyboardButton(f"📂 {f} ({v_count} Vids){status_text}", callback_data=f"view_folder_{f}"))

    inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))

    try:
        bot.edit_message_text(pass_instruction, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=inline, parse_mode="Markdown")
    except Exception:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, pass_instruction, reply_markup=inline, parse_mode="Markdown")


# ================= VIEW FOLDER DETAILS =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("view_folder_"))
def view_folder_cb(call):
    user_id = call.from_user.id
    folder = call.data.replace("view_folder_", "").strip()
    f_price = get_config(f"folder_price_{folder}") or "49"
    vids = get_videos(folder) or []
    vids_count = len(vids)

    inline = telebot.types.InlineKeyboardMarkup(row_width=1)

    if is_admin(user_id):
        inline.add(telebot.types.InlineKeyboardButton("🔄 Test Send Videos", callback_data=f"refetch_pass_{folder}"))
        inline.add(telebot.types.InlineKeyboardButton("🔙 Back to Folders", callback_data="folder_pass_menu"))
        inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
        
        text = (
            f"⚙️ **ADMIN FOLDER VIEW**\n\n"
            f"📂 **Folder:** `{folder}`\n"
            f"🎬 **Total Videos:** `{vids_count}`\n"
            f"💰 **Current Price:** ₹{f_price}\n\n"
            f"✏️ *Price badalne ke liye:*\n`/setfolderprice {folder} PRICE`"
        )
    else:
        is_unlocked = has_folder_access_db(user_id, folder)

        if is_unlocked:
            inline.add(telebot.types.InlineKeyboardButton(f"📥 Download & Share {folder}", callback_data=f"refetch_pass_{folder}"))
            status_info = "✅ **Is folder ka Full Access Pass Unlocked hai!**"
        else:
            inline.add(telebot.types.InlineKeyboardButton(f"💳 Buy Folder Pass (₹{f_price})", callback_data=f"buy_folder_{folder}"))
            status_info = f"🔒 **Status:** Locked\n💰 **Pass Price:** ₹{f_price}"

        inline.add(telebot.types.InlineKeyboardButton("🔙 Back to Folders", callback_data="folder_pass_menu"))
        inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))

        text = f"📂 **FOLDER:** `{folder}`\n🎬 **Total Videos:** `{vids_count}`\n\n{status_info}"

    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=inline, parse_mode="Markdown")
    except Exception:
        bot.send_message(call.message.chat.id, text, reply_markup=inline, parse_mode="Markdown")


# ================= BUY SPECIFIC PASS =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_folder_"))
def buy_folder_cb(call):
    user_id = call.from_user.id
    folder = call.data.replace("buy_folder_", "").strip()
    f_price = get_config(f"folder_price_{folder}") or "49"
    upi_id = get_config("upi_id") or "example@upi"

    user_pending_folder[user_id] = folder
    upi_url = f"upi://pay?pa={upi_id}&pn=Premium&am={f_price}&cu=INR"

    inline = telebot.types.InlineKeyboardMarkup(row_width=1)
    inline.add(
        telebot.types.InlineKeyboardButton("💳 I Have Paid", callback_data=f"paid_folder_{folder}"),
        telebot.types.InlineKeyboardButton("🔙 Back to Folders", callback_data="folder_pass_menu"),
        telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
    )

    caption_text = (
        f"📂 **BUY FOLDER PASS:** `{folder}`\n"
        f"💰 **Amount:** ₹{f_price}\n"
        f"📌 **UPI ID:** `{upi_id}` *(Tap to copy)*\n\n"
        f"👉 Payment karne ke baad [ 💳 I Have Paid ] button dabayein aur Screenshot bhej dein!"
    )

    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&margin=10&bgcolor=ffffff&color=000000&data={urllib.parse.quote(upi_url)}"

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    try:
        bot.send_photo(call.message.chat.id, photo=qr_api, caption=caption_text, reply_markup=inline, parse_mode="Markdown")
    except Exception:
        bot.send_message(call.message.chat.id, caption_text, reply_markup=inline, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("paid_folder_"))
def paid_folder_prompt(call):
    folder = call.data.replace("paid_folder_", "").strip()
    user_pending_folder[call.from_user.id] = folder

    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))

    text = (
        f"📸 **PAYMENT SCREENSHOT BHEJEIN** 📸\n\n"
        f"👉 **Folder `{folder}` ke payment ka Screenshot abhi chat me bhej dein!**"
    )

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot.send_message(call.message.chat.id, text, reply_markup=inline, parse_mode="Markdown")


# ================= RE-FETCH / SHARE FOLDER =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("refetch_pass_"))
def refetch_pass_cb(call):
    user_id = call.from_user.id
    folder = call.data.replace("refetch_pass_", "").strip()

    is_unlocked = is_admin(user_id) or has_folder_access_db(user_id, folder)

    if not is_unlocked:
        bot.answer_callback_query(call.id, f"❌ Folder `{folder}` ka pass buy karein!", show_alert=True)
        return

    vids = get_videos(folder) or []
    if not vids:
        bot.send_message(call.message.chat.id, f"❌ Folder `{folder}` currently empty hai.")
        return

    sent_ids = []
    for v in vids:
        m = bot.send_video(call.message.chat.id, v["file_id"], protect_content=False, caption=f"📂 `{folder}`\n⚠️ Auto-delete in 15 minutes!", parse_mode="Markdown")
        sent_ids.append(m.message_id)

    set_expiry(user_id, sent_ids, call.message.chat.id, time.time() + 900)

    inline = telebot.types.InlineKeyboardMarkup(row_width=1)
    inline.add(
        telebot.types.InlineKeyboardButton("🔄 Re-fetch Videos", callback_data=f"refetch_pass_{folder}"),
        telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
    )
    bot.send_message(call.message.chat.id, f"⏳ 15 Minutes Timer Started for `{folder}`!", reply_markup=inline, parse_mode="Markdown")


# ================= CHANNEL AUTO SAVE =================
@bot.channel_post_handler(content_types=['video'])
def auto_save_channel(msg):
    add_video(channel_folder, msg.video.file_id)
    print(f"Saved in folder: {channel_folder}")


# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Not allowed")
        return

    text = (
        "🛠 ADMIN PANEL\n\n"
        "⚙️ SETTINGS:\n"
        "✏️ /setstart TEXT\n"
        "🖼 /setimage (Set Banner Photo)\n"
        "🎬 /setdemo (Set Demo Video)\n"
        "💰 /setprice PRICE\n"
        "📂 /setfolderprice FOLDER_NAME PRICE\n"
        "📝 /setpasstext YOUR_CUSTOM_TEXT\n"
        "💳 /setupi YOUR_UPI_ID\n\n"
        "💳 /requests\n"
        "📢 /broadcast MESSAGE\n"
        "📊 /stats\n\n"
        "📂 /setfolder NAME\n"
        "📂 /setchannelfolder NAME\n"
        "📁 /folders\n"
        "🗑 /delfolder NAME\n"
        "❌ /delvideo INDEX"
    )

    bot.send_message(msg.chat.id, text)


# ================= SETTINGS COMMANDS =================
@bot.message_handler(commands=['setchannelfolder'])
def set_channel_folder(msg):
    global channel_folder
    if not is_admin(msg.from_user.id):
        return

    name = msg.text.replace("/setchannelfolder", "").strip()
    channel_folder = name
    bot.reply_to(msg, f"✅ Channel folder set: {name}")


@bot.message_handler(commands=['setstart'])
def setstart(msg):
    if not is_admin(msg.from_user.id):
        return
    text = msg.text.replace("/setstart", "").strip()
    set_config("start_text", text)
    bot.reply_to(msg, "✅ Start text updated!")


@bot.message_handler(commands=['setprice'])
def setprice(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split(" ", 1)
    if len(parts) > 1:
        set_config("price", parts[1].strip())
        bot.reply_to(msg, f"✅ Main Premium Price set to ₹{parts[1].strip()}")


@bot.message_handler(commands=['setupi'])
def setupi(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split(" ", 1)
    if len(parts) > 1:
        set_config("upi_id", parts[1].strip())
        bot.reply_to(msg, f"✅ UPI ID set to: `{parts[1].strip()}`", parse_mode="Markdown")


@bot.message_handler(commands=['setfolderprice'])
def setfolderprice(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split(" ", 2)
    if len(parts) < 3:
        bot.reply_to(msg, "❌ Usage: /setfolderprice FOLDER_NAME PRICE")
        return

    fname, fprice = parts[1].strip(), parts[2].strip()
    set_config(f"folder_price_{fname}", fprice)
    bot.reply_to(msg, f"✅ Folder '{fname}' price set to ₹{fprice}")


@bot.message_handler(commands=['setpasstext'])
def setpasstext(msg):
    if not is_admin(msg.from_user.id):
        return
    new_text = msg.text.replace("/setpasstext", "").strip()
    if not new_text:
        bot.reply_to(msg, "❌ Usage: /setpasstext YOUR_CUSTOM_TEXT")
        return

    set_config("pass_text", new_text)
    bot.reply_to(msg, "✅ Folder Pass text updated!")


@bot.message_handler(commands=['setdemo'])
def setdemo_cmd(msg):
    if is_admin(msg.from_user.id):
        admin_states[msg.from_user.id] = "awaiting_demo_content"
        bot.reply_to(msg, "🎬 Abhi Demo Video/Photo text ke saath bhejo:")


@bot.message_handler(commands=['setimage'])
def setimage_cmd(msg):
    if is_admin(msg.from_user.id):
        admin_states[msg.from_user.id] = "awaiting_start_image"
        bot.reply_to(msg, "📸 Abhi start banner image bhejo:")


# ================= BROADCAST & STATS =================
@bot.message_handler(commands=['broadcast'])
def broadcast_msg(msg):
    if is_admin(msg.from_user.id):
        text = msg.text.replace("/broadcast", "").strip()
        if not text:
            bot.reply_to(msg, "❌ Text bhi likhein: /broadcast Aapka Message")
            return

        db_users = get_all_users() or []
        users = list(set(list(db_users) + list(all_user_ids)))

        sent = 0
        for uid in users:
            try:
                bot.send_message(uid, text)
                sent += 1
                time.sleep(0.04)
            except Exception:
                pass
        bot.reply_to(msg, f"✅ Broadcast Sent to {sent} users!")


@bot.message_handler(commands=['stats'])
def stats(msg):
    if is_admin(msg.from_user.id):
        try:
            db_users = get_all_users() or []
            users_count = len(set(list(db_users) + list(all_user_ids)))
            folders_count = len(get_folders() or [])

            stats_text = (
                "📊 BOT STATS\n\n"
                f"👥 Total Users: {users_count}\n"
                f"📂 Total Folders: {folders_count}"
            )
            bot.send_message(msg.chat.id, stats_text)
        except Exception as e:
            bot.send_message(msg.chat.id, f"⚠️ Stats Error: {e}")


# ================= MEDIA HANDLER =================
@bot.message_handler(content_types=['photo', 'video'])
def handle_media(msg):
    track_user(msg.from_user.id)
    user_id = msg.from_user.id

    if is_admin(user_id) and admin_states.get(user_id) == "awaiting_demo_content":
        if msg.content_type == "video":
            set_config("demo_file_id", msg.video.file_id)
            set_config("demo_type", "video")
        elif msg.content_type == "photo":
            set_config("demo_file_id", msg.photo[-1].file_id)
            set_config("demo_type", "photo")

        caption = msg.caption or "👁️ Here is our Demo Content!"
        set_config("demo_text", caption)
        admin_states[user_id] = None
        bot.reply_to(msg, "✅ Demo updated successfully!")
        return

    if is_admin(user_id) and admin_states.get(user_id) == "awaiting_start_image" and msg.content_type == "photo":
        set_config("start_image", msg.photo[-1].file_id)
        admin_states[user_id] = None
        bot.reply_to(msg, "✅ Start Banner Photo updated!")
        return

    if is_admin(user_id) and msg.content_type == "video":
        if user_id not in current_folder:
            bot.reply_to(msg, "❌ Use /setfolder first")
            return
        folder = current_folder[user_id]
        add_video(folder, msg.video.file_id)
        bot.reply_to(msg, f"✅ Saved in {folder}")
        return

    if msg.content_type == "photo":
        pending_folder = user_pending_folder.get(user_id, "ONLINE_VIP_PLAN")
        add_pending(user_id, msg.photo[-1].file_id)
        set_config(f"pending_type_{user_id}", pending_folder)
        bot.send_message(msg.chat.id, f"⏳ Payment Screenshot Received for '{pending_folder}'! Wait for admin approval.")


# ================= REQUESTS APPROVAL =================
@bot.message_handler(commands=['requests'])
def requests_cmd(msg):
    if not is_admin(msg.from_user.id):
        return

    pending = get_pending()
    if not pending:
        bot.send_message(msg.chat.id, "❌ No pending requests")
        return

    for d in pending:
        uid = d["user_id"]
        ptype = get_config(f"pending_type_{uid}") or "ONLINE_VIP_PLAN"
        
        if ptype == "ONLINE_VIP_PLAN":
            f_price = get_config("price") or "29"
        else:
            f_price = get_config(f"folder_price_{ptype}") or "49"

        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(
            telebot.types.InlineKeyboardButton(f"✅ Approve ({ptype})", callback_data=f"apv_{uid}_{ptype}"),
            telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}")
        )

        bot.send_photo(
            msg.chat.id,
            d["file_id"],
            caption=f"📩 PAYMENT REQUEST\n\n👤 User: `{uid}`\n📂 Request For: `{ptype}`\n💰 Price: ₹{f_price}",
            reply_markup=kb,
            parse_mode="Markdown"
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith("apv_"))
def approve(call):
    parts = call.data.split("_")
    uid = int(parts[1])
    ptype = parts[2] if len(parts) > 2 else "ONLINE_VIP_PLAN"

    remove_pending(uid)

    inline = telebot.types.InlineKeyboardMarkup()

    if ptype == "ONLINE_VIP_PLAN":
        add_premium(uid)
        user_msg = (
            "🎉 **MAIN PREMIUM APPROVED!** 🎉\n\n"
            "📥 Click **'Download'** button to view videos (Protected Watch View)."
        )
        inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
    else:
        grant_folder_access_db(uid, ptype)
        user_msg = (
            f"🎉 **FOLDER PASS APPROVED FOR `{ptype}`!** 🎉\n\n"
            f"📂 You can now download and share videos of this folder from **Folder Passes** menu!"
        )
        inline.add(telebot.types.InlineKeyboardButton(f"📂 Open Folder {ptype}", callback_data=f"view_folder_{ptype}"))
        inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))

    try:
        bot.send_message(uid, user_msg, reply_markup=inline, parse_mode="Markdown")
    except Exception as e:
        print(f"User Notification Error: {e}")

    bot.send_message(call.message.chat.id, f"✅ Approved user {uid} for `{ptype}`!", parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):
    parts = call.data.split("_")
    uid = int(parts[1])
    remove_pending(uid)
    
    try:
        bot.send_message(uid, "❌ **Your Payment Request was Rejected.** Please check payment details or contact admin.", parse_mode="Markdown")
    except Exception:
        pass
        
    bot.send_message(call.message.chat.id, f"❌ Rejected user {uid}")


# ================= FOLDER MANAGEMENT =================
@bot.message_handler(commands=['setfolder'])
def setfolder(msg):
    if not is_admin(msg.from_user.id):
        return

    name = msg.text.replace("/setfolder", "").strip()
    if not name:
        bot.reply_to(msg, "❌ Use /setfolder NAME")
        return

    current_folder[msg.from_user.id] = name
    bot.reply_to(msg, f"📂 Active folder: {name}")


@bot.message_handler(commands=['folders'])
def showfolders(msg):
    data = get_folders() or []
    text = "📂 Folders:\n\n"
    for f in data:
        f_price = get_config(f"folder_price_{f}") or "49"
        vids = get_videos(f) or []
        count = len(vids)
        text += f"👉 `{f}` ({count} vids) - Pass: ₹{f_price}\n"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=['delfolder'])
def delfolder(msg):
    if not is_admin(msg.from_user.id):
        return

    name = msg.text.replace("/delfolder", "").strip()
    delete_folder(name)
    bot.reply_to(msg, f"🗑 Deleted {name}")


@bot.message_handler(commands=['delvideo'])
def delvideo(msg):
    if not is_admin(msg.from_user.id):
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


# ================= DOWNLOAD BUTTON =================
@bot.message_handler(func=lambda m: m.text == "📥 Download")
def download(msg):
    track_user(msg.from_user.id)
    
    if not is_premium(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Main Premium required to watch videos!", parse_mode="Markdown")
        return

    user_id = msg.from_user.id
    temp_access[user_id] = True

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    folders = get_folders() or []

    if not folders:
        bot.send_message(msg.chat.id, "❌ No folders available")
        return

    for f in folders:
        kb.add(f"📂 {f}")

    bot.send_message(msg.chat.id, "⏳ Select folder to watch videos:", reply_markup=kb)


# ================= OPEN FOLDER =================
@bot.message_handler(func=lambda m: m.text.startswith("📂 "))
def open_folder(msg):
    user_id = msg.from_user.id
    track_user(user_id)

    folder = msg.text.replace("📂 ", "").strip()

    if not is_admin(user_id) and not is_premium(user_id) and not has_folder_access_db(user_id, folder) and user_id not in temp_access:
        bot.send_message(msg.chat.id, f"🔒 **Folder `{folder}` is Locked!** Buy Premium or Folder Pass to view.", parse_mode="Markdown")
        return

    vids = get_videos(folder) or []

    if not vids:
        bot.send_message(msg.chat.id, "❌ No videos in this folder.")
        return

    sent_videos[user_id] = []
    for v in vids:
        m = bot.send_video(msg.chat.id, v["file_id"], protect_content=True, caption="⚠️ Auto-delete in 25 minutes!")
        sent_videos[user_id].append(m.message_id)

    set_expiry(
        user_id,
        sent_videos[user_id],
        msg.chat.id,
        time.time() + 1500
    )


# ================= RUN =================
print("Bot Running...")
bot.infinity_polling(skip_pending=True)
