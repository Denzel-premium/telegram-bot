import io
import random
import threading
import time
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
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
user_folder_access = {}
all_user_ids = set()

channel_folder = "DEFAULT"


def track_user(user_id):
    all_user_ids.add(user_id)
    try:
        add_user(user_id)
    except Exception:
        pass


def grant_folder_access(user_id, folder_name):
    if user_id not in user_folder_access:
        user_folder_access[user_id] = []
    if folder_name not in user_folder_access[user_id]:
        user_folder_access[user_id].append(folder_name)


def has_folder_access(user_id, folder_name):
    return (
        user_id in user_folder_access
        and folder_name in user_folder_access[user_id]
    )


# ================= ROYAL STANDEE GENERATOR (RAILWAY SAFE & COMPACT) =================
def create_custom_qr_standee(upi_url, price_text):
    width, height = 450, 700
    img = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # 1. Outer Frame
    draw.rectangle([15, 15, width - 15, height - 15], outline="#D4AF37", width=4)
    draw.rectangle([22, 22, width - 22, height - 22], outline="#F3E5AB", width=2)

    # 2. Header Branding
    draw.text((width // 2, 55), "👑", fill="#D4AF37", anchor="mm")
    draw.text((width // 2, 100), "DENZEL PREMIUM", fill="#000000", anchor="mm")
    draw.text((width // 2, 140), f"Pay Rs.{price_text} Here", fill="#D4AF37", anchor="mm")

    # 3. Compact QR Code Fetch
    qr_api = (
        f"https://api.qrserver.com/v1/create-qr-code/?"
        f"size=200x200&margin=12&bgcolor=ffffff&color=000000&"
        f"data={urllib.parse.quote(upi_url)}"
    )
    res = requests.get(qr_api, timeout=10)
    qr_img = Image.open(io.BytesIO(res.content))

    qr_x, qr_y = (width - 200) // 2, 190
    img.paste(qr_img, (qr_x, qr_y))

    draw.rectangle([qr_x - 6, qr_y - 6, qr_x + 200 + 6, qr_y + 200 + 6], outline="#D4AF37", width=3)

    # 4. Footer & Stand Base
    draw.text((width // 2, 440), "Scan & Pay for VIP Access", fill="#333333", anchor="mm")
    draw.rectangle([50, 490, width - 50, 508], fill="#D4AF37")
    draw.rectangle([75, 508, width - 75, 518], fill="#AA7C11")
    draw.text((width // 2, 570), "✨ Thank You For Choosing Us ✨", fill="#888888", anchor="mm")

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio


# ================= EXPIRY WORKER =================
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
                    except Exception:
                        pass
                delete_expiry(item["_id"])

        except Exception as e:
            print("Expiry error:", e)

        time.sleep(15)


threading.Thread(target=expiry_worker, daemon=True).start()


# ================= START =================
@bot.message_handler(commands=["start"])
def start(msg):
    track_user(msg.from_user.id)

    text = get_config("start_text") or "👋 Welcome to Premium Bot"
    price = get_config("price") or "29"
    start_image = get_config("start_image")

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📥 Download")

    inline = telebot.types.InlineKeyboardMarkup(row_width=1)
    inline.add(
        telebot.types.InlineKeyboardButton("💎 Buy Premium", callback_data="generate_qr"),
        telebot.types.InlineKeyboardButton("👁️ Demo", callback_data="show_demo"),
        telebot.types.InlineKeyboardButton("💳 I Have Paid", callback_data="paid_main"),
        telebot.types.InlineKeyboardButton("📂 Folder Passes", callback_data="folder_pass_menu"),
    )

    caption_full = (
        f"**{text}**\n\n"
        f"💰 **Online Watch Premium: ₹{price}**\n\n"
        f"👇 **Niche Diye Gaye Buttons Ka Use Karein:**"
    )

    if start_image:
        try:
            bot.send_photo(msg.chat.id, photo=start_image, caption=caption_full, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            bot.send_message(msg.chat.id, caption_full, reply_markup=kb, parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, caption_full, reply_markup=kb, parse_mode="Markdown")

    bot.send_message(msg.chat.id, "👇 **Select option below:**", reply_markup=inline, parse_mode="Markdown")


# ================= BUY PREMIUM (VIP PLAN STANDEE QR) =================
@bot.callback_query_handler(func=lambda call: call.data == "generate_qr")
def generate_qr_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    price = get_config("price") or "29"
    upi_id = get_config("upi_id") or "example@upi"
    upi_url = f"upi://pay?pa={upi_id}&pn=DenzelPremium&am={price}&cu=INR"

    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton("💳 Upload Screenshot", callback_data="paid_main"))

    caption_text = (
        f"👑 **DENZEL PREMIUM VIP ACCESS** 👑\n\n"
        f"📱 **SCAN & PAY ₹{price}**\n\n"
        f"📌 **UPI ID:** `{upi_id}` *(Tap text to Copy)*\n"
        f"💰 **Amount:** ₹{price}\n\n"
        f"👇 **Scan QR or copy UPI ID to pay, then click 'Upload Screenshot' below!**"
    )

    try:
        standee_img = create_custom_qr_standee(upi_url, f"{price}")
        bot.send_photo(
            call.message.chat.id,
            photo=standee_img,
            caption=caption_text,
            reply_markup=inline,
            parse_mode="Markdown",
        )
    except Exception as e:
        print("QR Error:", e)
        qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(upi_url)}"
        bot.send_photo(call.message.chat.id, photo=qr_api, caption=caption_text, reply_markup=inline, parse_mode="Markdown")


# ================= DEMO HANDLER =================
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
    demo_text = get_config("demo_text") or "👁️ **Here is our Demo Content!**"

    if not demo_file and not demo_text:
        bot.send_message(chat_id, "❌ **Demo content currently available nahi hai.**", parse_mode="Markdown")
        return

    buy_kb = telebot.types.InlineKeyboardMarkup()
    buy_kb.add(telebot.types.InlineKeyboardButton("💎 Buy Premium", callback_data="generate_qr"))

    sent_demo_ids = []
    demo_caption = (
        f"{demo_text}\n\n"
        f"🚨 **LIMITED TIME DEMO ACCESS** 🚨\n"
        f"⚠️ **Yeh demo content 10 minute me automatically delete ho jayega!**"
    )

    if demo_type == "video" and demo_file:
        m1 = bot.send_video(chat_id, video=demo_file, caption=demo_caption, parse_mode="Markdown", reply_markup=buy_kb, protect_content=True)
        sent_demo_ids.append(m1.message_id)
    elif demo_type == "photo" and demo_file:
        m1 = bot.send_photo(chat_id, photo=demo_file, caption=demo_caption, parse_mode="Markdown", reply_markup=buy_kb)
        sent_demo_ids.append(m1.message_id)
    else:
        m1 = bot.send_message(chat_id, f"{demo_caption}", parse_mode="Markdown", reply_markup=buy_kb)
        sent_demo_ids.append(m1.message_id)

    set_expiry(user_id, sent_demo_ids, chat_id, time.time() + 600)


# ================= DIRECT SCREENSHOT OPTION =================
@bot.callback_query_handler(func=lambda call: call.data == "paid_main")
def paid_main_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    user_pending_folder[call.from_user.id] = "ONLINE_VIP_PLAN"
    bot.send_message(call.message.chat.id, "📸 **Payment hone ke baad yahan Screenshot bhejo.**", parse_mode="Markdown")


# ================= FOLDER PASSES MENU =================
@bot.callback_query_handler(func=lambda call: call.data == "folder_pass_menu")
def folder_pass_menu(call):
    user_id = call.from_user.id
    folders = get_folders()
    if not folders:
        bot.send_message(call.message.chat.id, "❌ **No folders available**", parse_mode="Markdown")
        return

    default_text = (
        "📁 **PER-FOLDER ACCESS PASS**\n\n"
        "💡 **Kaise Kaam Karta Hai?**\n"
        "👉 Niche se apna **Folder Select** karein aur uska **Pass Buy** karein.\n"
        "👉 Approval milte hi folder ki saari videos aapko bhej di jayengi.\n\n"
        "⏱️ **15 Minute Auto-Delete:**\n"
        "⚠️ Security ke liye videos **15 minute me auto-delete** ho jayengi.\n\n"
        "🔄 **Lifetime Re-Fetch Access:**\n"
        "🎉 Access Pass hone par aap **`🔄 Re-fetch`** button daba kar kitni bhi baar videos **DOHBARA** 15 min ke liye mangwa sakte hain!\n\n"
        "👇 **Niche Folder Select Karein:**"
    )

    pass_instruction = get_config("pass_text") or default_text

    inline = telebot.types.InlineKeyboardMarkup()
    for f in folders:
        f_price = get_config(f"folder_price_{f}") or "49"
        status_text = " ✅" if has_folder_access(user_id, f) else f" • ₹{f_price}"
        inline.add(telebot.types.InlineKeyboardButton(f"📂 {f}{status_text}", callback_data=f"view_folder_{f}"))

    bot.send_message(call.message.chat.id, pass_instruction, reply_markup=inline, parse_mode="Markdown")


# ================= VIEW FOLDER DETAILS & BUY/RE-FETCH =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("view_folder_"))
def view_folder_cb(call):
    user_id = call.from_user.id
    folder = call.data.replace("view_folder_", "").strip()
    f_price = get_config(f"folder_price_{folder}") or "49"
    vids_count = len(get_videos(folder))

    inline = telebot.types.InlineKeyboardMarkup()

    if has_folder_access(user_id, folder):
        inline.add(telebot.types.InlineKeyboardButton(f"🔄 Re-fetch `{folder}`", callback_data=f"refetch_pass_{folder}"))
        status_info = (
            "✅ **Aapke paas is folder ka Approved Pass hai!**\n"
            "Videos 15 min me delete hone ke baad aap jab chahe Re-fetch kar sakte hain."
        )
    else:
        inline.add(telebot.types.InlineKeyboardButton("💎 Buy Pass", callback_data=f"buy_folder_{folder}"))
        status_info = (
            f"💰 **Download Pass Price:** ₹{f_price}\n"
            f"📌 *Is pass ko buy karne se videos 15 min timer + Infinite Re-Fetch Access ke sath milengi!*"
        )

    bot.send_message(
        call.message.chat.id,
        f"📂 **FOLDER:** `{folder}`\n🎬 **Total Videos:** `{vids_count}`\n\n{status_info}",
        reply_markup=inline,
        parse_mode="Markdown"
    )


# ================= GENERATE STANDEE QR FOR SPECIFIC FOLDER =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_folder_"))
def buy_folder_cb(call):
    user_id = call.from_user.id
    folder = call.data.replace("buy_folder_", "").strip()
    f_price = get_config(f"folder_price_{folder}") or "49"
    upi_id = get_config("upi_id") or "example@upi"

    user_pending_folder[user_id] = folder
    upi_url = f"upi://pay?pa={upi_id}&pn=DenzelPremium&am={f_price}&cu=INR"

    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton("📸 Send Screenshot", callback_data=f"paid_folder_{folder}"))

    caption_text = (
        f"👑 **DENZEL PREMIUM - FOLDER PASS** 👑\n\n"
        f"📂 **Selected Folder:** `{folder}`\n"
        f"💰 **Pass Amount:** ₹{f_price}\n"
        f"📌 **UPI ID:** `{upi_id}` *(Tap to Copy)*\n\n"
        f"👇 **Scan QR karke ₹{f_price} pay karein aur 'Send Screenshot' button par click karke photo bhejein!**"
    )

    try:
        standee_img = create_custom_qr_standee(upi_url, f"{f_price}")
        bot.send_photo(
            call.message.chat.id,
            photo=standee_img,
            caption=caption_text,
            reply_markup=inline,
            parse_mode="Markdown",
        )
    except Exception as e:
        print("Folder QR Error:", e)
        qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(upi_url)}"
        bot.send_photo(call.message.chat.id, photo=qr_api, caption=caption_text, reply_markup=inline, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("paid_folder_"))
def paid_folder_prompt(call):
    folder = call.data.replace("paid_folder_", "").strip()
    user_pending_folder[call.from_user.id] = folder
    bot.send_message(call.message.chat.id, f"📸 **Abhi payment ka Screenshot yahan bhejein (Folder: `{folder}`):**", parse_mode="Markdown")


# ================= RE-FETCH PASS HANDLER =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("refetch_pass_"))
def refetch_pass_cb(call):
    user_id = call.from_user.id
    folder = call.data.replace("refetch_pass_", "").strip()

    if not has_folder_access(user_id, folder):
        bot.answer_callback_query(call.id, f"❌ Aapke paas '{folder}' ka active pass nahi hai!", show_alert=True)
        return

    vids = get_videos(folder)
    if not vids:
        bot.send_message(call.message.chat.id, f"❌ **Folder `{folder}` is empty.**", parse_mode="Markdown")
        return

    sent_ids = []
    warning_caption = "⚠️ *This video will auto-delete in 15 minutes! Re-fetch anytime.*"

    for v in vids:
        m = bot.send_video(call.message.chat.id, v["file_id"], protect_content=False, caption=warning_caption, parse_mode="Markdown")
        sent_ids.append(m.message_id)

    set_expiry(user_id, sent_ids, call.message.chat.id, time.time() + 900)

    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton("🔄 Re-fetch Videos", callback_data=f"refetch_pass_{folder}"))

    bot.send_message(
        call.message.chat.id,
        f"⏳ **15 Minutes Timer Started for `{folder}`!**\nVideos delete hone ke baad niche button se dobara Mangwa sakte hain:",
        reply_markup=inline,
        parse_mode="Markdown"
    )


# ================= CHANNEL AUTO SAVE =================
@bot.channel_post_handler(content_types=["video"])
def auto_save_channel(msg):
    add_video(channel_folder, msg.video.file_id)
    print(f"Saved in folder: {channel_folder}")


# ================= ADMIN PANEL (FIXED DATA-TYPE COMPARISON) =================
@bot.message_handler(commands=["admin"])
def admin(msg):
    # User ID aur ADMIN_ID dono ko strict string banakar strip karte hain taaki extra space ya quotes se issue na aaye
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()

    if user_id_str != admin_id_str:
        bot.send_message(msg.chat.id, "❌ **Not allowed**", parse_mode="Markdown")
        return

    text = (
        "🛠 **ADMIN PANEL**\n\n"
        "⚙️ **SETTINGS:**\n"
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
        "📁 /folders\n"
        "🗑 /delfolder NAME\n"
        "❌ /delvideo INDEX\n"
    )

    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


# ================= SET FOLDER PRICE & PASS TEXT =================
@bot.message_handler(commands=["setfolderprice"])
def setfolderprice(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str != admin_id_str:
        return

    parts = msg.text.split(" ", 2)
    if len(parts) < 3:
        bot.reply_to(msg, "❌ **Usage:** `/setfolderprice FOLDER_NAME PRICE`", parse_mode="Markdown")
        return

    fname, fprice = parts[1].strip(), parts[2].strip()
    set_config(f"folder_price_{fname}", fprice)
    bot.reply_to(msg, f"✅ **Folder `{fname}` price set to ₹{fprice}**", parse_mode="Markdown")


@bot.message_handler(commands=["setpasstext"])
def setpasstext(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str != admin_id_str:
        return

    new_text = msg.text.replace("/setpasstext", "").strip()
    if not new_text:
        bot.reply_to(msg, "❌ **Usage:** `/setpasstext YOUR_CUSTOM_TEXT`", parse_mode="Markdown")
        return

    set_config("pass_text", new_text)
    bot.reply_to(msg, "✅ **Folder Pass instruction text updated successfully!**", parse_mode="Markdown")


# ================= MEDIA HANDLER =================
@bot.message_handler(content_types=["photo", "video"])
def handle_media(msg):
    track_user(msg.from_user.id)
    user_id = msg.from_user.id
    user_id_str = str(user_id).strip()
    admin_id_str = str(ADMIN_ID).strip()

    if user_id_str == admin_id_str and admin_states.get(ADMIN_ID) == "awaiting_demo_content":
        if msg.content_type == "video":
            set_config("demo_file_id", msg.video.file_id)
            set_config("demo_type", "video")
        elif msg.content_type == "photo":
            set_config("demo_file_id", msg.photo[-1].file_id)
            set_config("demo_type", "photo")

        caption = msg.caption or "👁️ **Here is our Demo Content!**"
        set_config("demo_text", caption)
        admin_states[ADMIN_ID] = None
        bot.reply_to(msg, "✅ **Demo updated successfully!**", parse_mode="Markdown")
        return

    if user_id_str == admin_id_str and admin_states.get(ADMIN_ID) == "awaiting_start_image" and msg.content_type == "photo":
        set_config("start_image", msg.photo[-1].file_id)
        admin_states[ADMIN_ID] = None
        bot.reply_to(msg, "✅ **Start Banner Photo updated!**", parse_mode="Markdown")
        return

    if user_id_str == admin_id_str and msg.content_type == "video":
        if user_id not in current_folder:
            bot.reply_to(msg, "❌ **Use /setfolder first**", parse_mode="Markdown")
            return
        folder = current_folder[user_id]
        add_video(folder, msg.video.file_id)
        bot.reply_to(msg, f"✅ **Saved in {folder}**", parse_mode="Markdown")
        return

    if msg.content_type == "photo":
        pending_folder = user_pending_folder.get(user_id, "ONLINE_VIP_PLAN")
        add_pending(user_id, msg.photo[-1].file_id)
        set_config(f"pending_type_{user_id}", pending_folder)

        bot.send_message(
            msg.chat.id,
            f"⏳ **Payment Screenshot Received for `{pending_folder}`! Wait for admin approval.**",
            parse_mode="Markdown",
        )


# ================= REQUESTS APPROVAL =================
@bot.message_handler(commands=["requests"])
def requests(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str != admin_id_str:
        return

    for d in get_pending():
        uid = d["user_id"]
        ptype = get_config(f"pending_type_{uid}") or "ONLINE_VIP_PLAN"
        f_price = get_config(f"folder_price_{ptype}") or "49" if ptype != "ONLINE_VIP_PLAN" else get_config("price") or "29"

        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(
            telebot.types.InlineKeyboardButton(f"✅ Approve ({ptype})", callback_data=f"apv_{uid}_{ptype}"),
            telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}"),
        )
        bot.send_photo(
            msg.chat.id,
            d["file_id"],
            caption=f"📩 **NEW PAYMENT REQUEST RECEIVED**\n\n👤 **User ID:** `{uid}`\n📂 **Folder/Plan:** `{ptype}`\n💰 **Set Price:** ₹{f_price}",
            reply_markup=kb,
            parse_mode="Markdown",
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith("apv_"))
def approve(call):
    parts = call.data.split("_")
    uid = int(parts[1])
    ptype = parts[2] if len(parts) > 2 else "ONLINE_VIP_PLAN"

    remove_pending(uid)

    if ptype == "ONLINE_VIP_PLAN":
        add_premium(uid)
        bot.send_message(uid, "🎉 **VIP Online Plan Approved!\n📥 Click 'Download' button below to view content.**", parse_mode="Markdown")
    else:
        grant_folder_access(uid, ptype)

        vids = get_videos(ptype)
        if not vids:
            bot.send_message(uid, f"🎉 **Approved Pass for `{ptype}`! But folder is empty.**", parse_mode="Markdown")
        else:
            bot.send_message(uid, f"🎉 **Approved Pass for `{ptype}`!\nSending videos now (Auto-Delete in 15 min, Re-fetch anytime)...**", parse_mode="Markdown")

            sent_ids = []
            for v in vids:
                m = bot.send_video(uid, v["file_id"], protect_content=False, caption=f"📂 **Folder:** `{ptype}`\n⚠️ *Auto-delete in 15 min.*")
                sent_ids.append(m.message_id)

            set_expiry(uid, sent_ids, uid, time.time() + 900)

            inline = telebot.types.InlineKeyboardMarkup()
            inline.add(telebot.types.InlineKeyboardButton("🔄 Re-fetch Videos", callback_data=f"refetch_pass_{ptype}"))
            bot.send_message(uid, f"⏳ **15 Minutes Timer Started for `{ptype}`!**\nVideos delete hone ke baad dobara Re-fetch karein:", reply_markup=inline, parse_mode="Markdown")

    bot.send_message(call.message.chat.id, f"✅ **Approved user {uid} for `{ptype}`!**", parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):
    uid = int(call.data.split("_")[1])
    remove_pending(uid)
    bot.send_message(uid, "❌ **Payment Rejected**", parse_mode="Markdown")


# ================= OTHER ADMIN COMMANDS =================
@bot.message_handler(commands=["setdemo"])
def setdemo_cmd(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str == admin_id_str:
        admin_states[msg.from_user.id] = "awaiting_demo_content"
        bot.reply_to(msg, "🎬 **Abhi Demo Video/Photo text ke saath bhejo:**", parse_mode="Markdown")


@bot.message_handler(commands=["setimage"])
def setimage_cmd(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str == admin_id_str:
        admin_states[msg.from_user.id] = "awaiting_start_image"
        bot.reply_to(msg, "📸 **Abhi start banner image bhejo:**", parse_mode="Markdown")


@bot.message_handler(commands=["setupi"])
def setupi(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str == admin_id_str:
        parts = msg.text.split(" ", 1)
        if len(parts) >= 2:
            set_config("upi_id", parts[1].strip())
            bot.reply_to(msg, f"✅ **UPI ID set to:** `{parts[1].strip()}`", parse_mode="Markdown")


@bot.message_handler(commands=["broadcast"])
def broadcast_msg(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str == admin_id_str:
        text = msg.text.replace("/broadcast", "").strip()
        if text:
            db_users = get_all_users() or []
            users = list(set(list(db_users) + list(all_user_ids)))
            for uid in users:
                try:
                    bot.send_message(uid, f"**{text}**", parse_mode="Markdown")
                    time.sleep(0.05)
                except Exception:
                    pass
            bot.reply_to(msg, "✅ **Broadcast Sent!**", parse_mode="Markdown")


@bot.message_handler(commands=["stats"])
def stats(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str == admin_id_str:
        db_users = get_all_users() or []
        users_count = len(set(list(db_users) + list(all_user_ids)))
        bot.send_message(msg.chat.id, f"📊 **BOT STATS**\n\n👥 **Total Users:** {users_count}\n📂 **Folders:** {len(get_folders())}", parse_mode="Markdown")


@bot.message_handler(commands=["setfolder"])
def setfolder(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str == admin_id_str:
        name = msg.text.replace("/setfolder", "").strip()
        current_folder[msg.from_user.id] = name
        bot.reply_to(msg, f"📂 **Active folder: {name}**", parse_mode="Markdown")


@bot.message_handler(commands=["folders"])
def showfolders(msg):
    data = get_folders()
    text = "📂 **Folders List:**\n\n"
    for f in data:
        f_price = get_config(f"folder_price_{f}") or "49"
        count = len(get_videos(f))
        text += f"👉 `{f}` ({count} videos) - Pass: ₹{f_price}\n"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["delfolder"])
def delfolder(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str == admin_id_str:
        name = msg.text.replace("/delfolder", "").strip()
        delete_folder(name)
        bot.reply_to(msg, f"🗑 **Deleted folder: {name}**", parse_mode="Markdown")


@bot.message_handler(commands=["delvideo"])
def delvideo(msg):
    user_id_str = str(msg.from_user.id).strip()
    admin_id_str = str(ADMIN_ID).strip()
    if user_id_str == admin_id_str:
        parts = msg.text.split(" ")
        if len(parts) >= 2:
            index = int(parts[1])
            folder = current_folder.get(msg.from_user.id)
            if folder:
                delete_video(folder, index)
                bot.reply_to(msg, "❌ **Video deleted**", parse_mode="Markdown")


# ================= ONLINE STREAMING DOWNLOAD (NORMAL PLAN) =================
@bot.message_handler(func=lambda m: m.text == "📥 Download")
def download(msg):
    track_user(msg.from_user.id)
    if not is_premium(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ **VIP Subscription required**", parse_mode="Markdown")
        return

    user_id = msg.from_user.id
    temp_access[user_id] = True

    folders = get_folders()
    if not folders:
        bot.send_message(msg.chat.id, "❌ **No folders available**", parse_mode="Markdown")
        return

    inline = telebot.types.InlineKeyboardMarkup()
    for f in folders:
        inline.add(telebot.types.InlineKeyboardButton(f"📂 {f}", callback_data=f"open_{f}"))

    bot.send_message(msg.chat.id, "📁 **Select a folder to view content online:**", reply_markup=inline, parse_mode="Markdown")


# ================= OPEN FOLDER =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("open_"))
def open_folder_cb(call):
    user_id = call.from_user.id
    track_user(user_id)

    if user_id not in temp_access and not is_premium(user_id):
        bot.send_message(call.message.chat.id, "❌ **VIP Subscription required!**", parse_mode="Markdown")
        return

    folder = call.data.replace("open_", "").strip()
    vids = get_videos(folder)

    if not vids:
        bot.send_message(call.message.chat.id, "❌ **No videos in this folder**", parse_mode="Markdown")
        return

    sent_videos[user_id] = []
    warning_caption = "⚠️ *This video will auto-delete in 15 minutes! Save or watch soon.*"

    for v in vids:
        m = bot.send_video(call.message.chat.id, v["file_id"], protect_content=True, caption=warning_caption, parse_mode="Markdown")
        sent_videos[user_id].append(m.message_id)

    set_expiry(user_id, sent_videos[user_id], call.message.chat.id, time.time() + 900)


# ================= RUN =================
print("Bot Running...")
bot.infinity_polling(skip_pending=True)
