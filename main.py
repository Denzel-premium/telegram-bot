

        )
    
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
        bot.answer_callback_query(call.id, f"❌ Access Revoked! Folder `{folder}` ka pass buy karein!", show_alert=True)
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
    bot.send_message(call.message.chat.id, f"⏳ 15 Minutes Timer Started for `{folder}` ({len(vids)} videos sent)!", reply_markup=inline, parse_mode="Markdown")


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
        "🛠 **ADMIN PANEL & USER MANAGEMENT**\n\n"
        "👥 **USER MANAGER:**\n"
        "👥 `/userlist` (View All Users Compact List)\n"
        "🔍 `/finduser USER_ID` (Search user & check date/time)\n"
        "🚫 `/revoke USER_ID [FOLDER_NAME]` (Direct Command Revoke)\n\n"
        "⚙️ **SETTINGS:**\n"
        "✏️ `/setstart TEXT`\n"
        "🖼 `/setimage` (Set Banner Photo)\n"
        "🎬 `/setdemo` (Set Demo Video)\n"
        "💰 `/setprice PRICE`\n"
        "📂 `/setfolderprice FOLDER_NAME PRICE`\n"
        "📝 `/setpasstext YOUR_CUSTOM_TEXT`\n"
        "💳 `/setupi YOUR_UPI_ID`\n\n"
        "📥 **REQUESTS:**\n"
        "💳 `/requests` (Pending Payments)\n\n"
        "📢 `/broadcast MESSAGE`\n"
        "📊 `/stats`\n\n"
        "📂 `/setfolder NAME`\n"
        "📂 `/setchannelfolder NAME`\n"
        "📁 `/folders`\n"
        "🗑 `/delfolder NAME`\n"
        "❌ `/delvideo INDEX`"
    )

    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


# ================= USER SEARCH COMMAND =================
@bot.message_handler(commands=['finduser'])
def finduser_cmd(msg):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.strip().split()
    if len(parts) < 2:
        bot.reply_to(msg, "❌ **Usage:** `/finduser USER_ID`", parse_mode="Markdown")
        return

    raw_uid = parts[1].replace("`", "").strip()
    if not raw_uid.isdigit():
        bot.reply_to(msg, "❌ Invalid User ID!")
        return

    render_user_details(msg.chat.id, int(raw_uid))


# ================= COMPACT USER LIST WITH SMALL FONT DATE/TIME & ACCESS DETAILS =================
def render_compact_user_list(chat_id, page=1, message_id=None):
    db_users = get_all_users() or []
    users = list(set(list(db_users) + list(all_user_ids)))
    folders = get_folders() or []

    if not users:
        bot.send_message(chat_id, "❌ No registered users found!")
        return

    per_page = 10
    total_users = len(users)
    total_pages = (total_users + per_page - 1) // per_page

    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_batch = users[start_idx:end_idx]

    list_text = f"📋 **USER LIST (Page {page}/{total_pages})**\n"
    list_text += f"👥 **Total Users:** `{total_users}`\n"
    list_text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    list_text += "*(ID tap karke copy karein ➔ `/finduser ID` ya `/revoke ID`)*\n\n"

    for idx, uid in enumerate(current_batch, start=start_idx + 1):
        is_vip = is_premium(uid)
        
        # Unlocked folders check
        unlocked = []
        for f in folders:
            if has_folder_access_db(uid, f):
                unlocked.append(f)

        # Status Build
        if is_vip:
            status_str = "👑 Main VIP"
        elif unlocked:
            status_str = f"📂 Folders ({len(unlocked)})"
        else:
            status_str = "👤 Free"

        list_text += f"{idx}. `{uid}` • **{status_str}**\n"

        # Display Small Font Date & Time for Main VIP
        if is_vip:
            v_time = get_config(f"vip_time_{uid}")
            list_text += f"   `📅 Main VIP ➔ {get_formatted_time(v_time, compact=True)}`\n"

        # Display Small Font Date & Time for Folders
        for f in unlocked:
            f_time = get_config(f"folder_time_{uid}_{f}")
            list_text += f"   `└ {f} ➔ {get_formatted_time(f_time, compact=True)}`\n"

        list_text += "\n"

    kb = telebot.types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    if page > 1:
        buttons.append(telebot.types.InlineKeyboardButton("◀️ Prev", callback_data=f"page_{page-1}"))
    if page < total_pages:
        buttons.append(telebot.types.InlineKeyboardButton("Next ▶️", callback_data=f"page_{page+1}"))

    if buttons:
        kb.add(*buttons)

    if message_id:
        try:
            bot.edit_message_text(list_text, chat_id=chat_id, message_id=message_id, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, list_text, reply_markup=kb, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, list_text, reply_markup=kb, parse_mode="Markdown")


@bot.message_handler(commands=['userlist'])
def userlist_cmd(msg):
    if not is_admin(msg.from_user.id):
        return
    render_compact_user_list(msg.chat.id, page=1)


@bot.callback_query_handler(func=lambda c: c.data.startswith("page_"))
def page_cb(call):
    if not is_admin(call.from_user.id):
        return
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    target_page = int(call.data.replace("page_", "").strip())
    render_compact_user_list(call.message.chat.id, page=target_page, message_id=call.message.message_id)


# ================= REVOKE ACCESS COMMAND =================
@bot.message_handler(commands=['revoke'])
def revoke_cmd(msg):
    if not is_admin(msg.from_user.id):
        return

    raw_text = msg.text.replace("/revoke", "").strip()
    parts = raw_text.split()

    if not parts:
        bot.reply_to(msg, "❌ **Usage:**\n`/revoke USER_ID` (Main Premium Revoke)\n`/revoke USER_ID FOLDER_NAME` (Folder Access Revoke)", parse_mode="Markdown")
        return

    clean_uid_str = parts[0].replace("`", "").replace("'", "").strip()

    if not clean_uid_str.isdigit():
        bot.reply_to(msg, "❌ Invalid User ID!")
        return

    target_uid = int(clean_uid_str)

    if len(parts) >= 2:
        folder_name = parts[1].strip()
        force_revoke_access(target_uid, folder_name)
        bot.reply_to(msg, f"🚫 Folder Access `{folder_name}` for user `{target_uid}` is REVOKED!", parse_mode="Markdown")
        try:
            bot.send_message(target_uid, f"⚠️ **ACCESS CANCELLED**\n\nAapka Folder Pass `{folder_name}` ka access cancel kar diya gaya hai.", parse_mode="Markdown")
        except Exception:
            pass
    else:
        force_revoke_access(target_uid, "ONLINE_VIP_PLAN")
        bot.reply_to(msg, f"🚫 Main Premium for user `{target_uid}` is REVOKED!", parse_mode="Markdown")
        try:
            bot.send_message(target_uid, "⚠️ **PREMIUM CANCELLED**\n\nAapka Main Premium Access cancel kar diya gaya hai.", parse_mode="Markdown")
        except Exception:
            pass


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


# ================= REQUESTS APPROVAL WITH LIVE STATUS UPDATES =================
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

        kb = telebot.types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            telebot.types.InlineKeyboardButton(f"✅ Approve ({ptype})", callback_data=f"apv_{uid}_{ptype}"),
            telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}")
        )

        bot.send_photo(
            msg.chat.id,
            d["file_id"],
            caption=f"📩 **PAYMENT REQUEST**\n\n👤 **User ID:** `{uid}` *(Tap to copy)*\n📂 **Request For:** `{ptype}`\n💰 **Price:** ₹{f_price}",
            reply_markup=kb,
            parse_mode="Markdown"
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith("apv_"))
def approve(call):
    try:
        bot.answer_callback_query(call.id, f"✅ Approved User {call.data.split('_')[1]}!", show_alert=True)
    except Exception:
        pass

    raw_data = call.data.replace("apv_", "")
    parts = raw_data.split("_", 1)
    uid = int(parts[0])
    ptype = parts[1] if len(parts) > 1 else "ONLINE_VIP_PLAN"

    remove_pending(uid)
    curr_time = time.time()

    inline = telebot.types.InlineKeyboardMarkup()

    if ptype == "ONLINE_VIP_PLAN":
        add_premium(uid)
        set_config(f"vip_time_{uid}", str(curr_time))
        user_msg = (
            "🎊 **PAYMENT VERIFIED & APPROVED!** 🎊\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "👑 **STATUS:** **APPROVED** ✅\n"
            "✨ **PLAN:** **MAIN PREMIUM VIP**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📥 Videos dekhne ke liye niche **'Download'** button par click karein aur apna folder select karein!"
        )
        inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
    else:
        grant_folder_access_db(uid, ptype)
        set_config(f"folder_time_{uid}_{ptype}", str(curr_time))
        vids_count = count_videos(ptype)
        user_msg = (
            "🎊 **PAYMENT VERIFIED & APPROVED!** 🎊\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "👑 **STATUS:** **APPROVED** ✅\n"
            f"📂 **FOLDER:** `{ptype}`\n"
            f"🎬 **TOTAL VIDEOS:** `{vids_count}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📥 Aap niche button se **Folder Passes** open karke videos download aur share kar sakte hain!"
        )
        inline.add(telebot.types.InlineKeyboardButton(f"📂 Open Folder {ptype}", callback_data=f"view_folder_{ptype}"))
        inline.add(telebot.types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))

    try:
        bot.send_message(uid, user_msg, reply_markup=inline, parse_mode="Markdown")
    except Exception as e:
        print(f"User Notification Error: {e}")

    admin_btn = telebot.types.InlineKeyboardMarkup()
    admin_btn.add(telebot.types.InlineKeyboardButton(f"🚫 Revoke Permission ({uid})", callback_data=f"btnrevoke_{uid}_{ptype}"))

    admin_ack_msg = (
        "✅ **STATUS:** **APPROVED**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **USER ID:** `{uid}`\n"
        f"📂 **REQUEST FOR:** `{ptype}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "*(Glti se approve hua ho toh niche button se revoke karein)*"
    )

    try:
        if getattr(call.message, 'content_type', None) == 'photo':
            bot.edit_message_caption(caption=admin_ack_msg, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_btn, parse_mode="Markdown")
        else:
            bot.edit_message_text(admin_ack_msg, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_btn, parse_mode="Markdown")
    except Exception:
        render_user_details(call.message.chat.id, uid, message_id=call.message.message_id)


# Safe Live Revoke Callback
@bot.callback_query_handler(func=lambda c: c.data.startswith("btnrevoke_"))
def button_revoke_cb(call):
    if not is_admin(call.from_user.id):
        return

    raw_data = call.data.replace("btnrevoke_", "")
    parts = raw_data.split("_", 1)
    uid = int(parts[0])
    ptype = parts[1] if len(parts) > 1 else "ONLINE_VIP_PLAN"

    # Database Access Complete Removal
    force_revoke_access(uid, ptype)

    try:
        bot.answer_callback_query(call.id, f"🚫 Access Revoked for User {uid}!", show_alert=True)
    except Exception:
        pass

    if ptype == "ONLINE_VIP_PLAN":
        user_notify = "⚠️ **PREMIUM CANCELLED**\n\nAapka Main Premium access cancel/revoke kar diya gaya hai."
    else:
        user_notify = f"⚠️ **ACCESS CANCELLED**\n\nAapka Folder `{ptype}` ka access cancel kar diya gaya hai."

    try:
        bot.send_message(uid, user_notify, parse_mode="Markdown")
    except Exception:
        pass

    revoked_ack_msg = (
        "🚫 **STATUS:** **REVOKED / CANCELLED**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **USER ID:** `{uid}`\n"
        f"📂 **ACCESS REMOVED:** `{ptype}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Access is user se successfully wapas le liya gaya hai.*"
    )

    try:
        if getattr(call.message, 'content_type', None) == 'photo':
            bot.edit_message_caption(caption=revoked_ack_msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        else:
            render_user_details(call.message.chat.id, uid, message_id=call.message.message_id)
    except Exception:
        try:
            render_user_details(call.message.chat.id, uid, message_id=call.message.message_id)
        except Exception:
            pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("rej_"))
def reject(call):
    try:
        bot.answer_callback_query(call.id, "❌ Payment Rejected!", show_alert=True)
    except Exception:
        pass

    raw_data = call.data.replace("rej_", "")
    uid = int(raw_data.split("_")[0])
    remove_pending(uid)
    
    try:
        bot.send_message(uid, "❌ **Your Payment Request was Rejected.** Please check payment details or contact admin.", parse_mode="Markdown")
    except Exception as e:
        print(f"Rejection Send Error: {e}")
        
    rejected_ack_msg = (
        "❌ **STATUS:** **REJECTED**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **USER ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Payment request reject kar di gayi hai aur user ko message chala gaya hai.*"
    )

    try:
        if getattr(call.message, 'content_type', None) == 'photo':
            bot.edit_message_caption(caption=rejected_ack_msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text(rejected_ack_msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    except Exception:
        pass


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
    
    # Check directly against DB
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

    # STRICT ACCESS CHECK
    has_folder_pass = has_folder_access_db(user_id, folder)
    has_vip = is_premium(user_id)
    
    if not is_admin(user_id) and not has_vip and not has_folder_pass:
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
