from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import *
from languages import t
from config import STORAGE_CHANNEL_ID

admin_states = {}

# =====================
# ADMIN MENYUSI
# =====================

def admin_menu_kb(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo'shish",       callback_data="adm_add_movie"),
         InlineKeyboardButton("🗑 Kino o'chirish",      callback_data="adm_del_movie")],
        [InlineKeyboardButton("📢 Obuna boshqarish",    callback_data="adm_subs"),
         InlineKeyboardButton("📊 Statistika",          callback_data="adm_stats")],
        [InlineKeyboardButton("📣 Xabar yuborish",      callback_data="adm_broadcast"),
         InlineKeyboardButton("👤 Admin qo'shish",      callback_data="adm_add_admin")],
        [InlineKeyboardButton("💎 VIP panel",           callback_data="adm_vip"),
         InlineKeyboardButton("⚙️ Sozlamalar",          callback_data="adm_settings")],
        [InlineKeyboardButton("📡 Qo'shimcha kanallar", callback_data="adm_extra_channels")],
        [InlineKeyboardButton("🔙 Orqaga",              callback_data="menu")],
    ])

def sub_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kanal qo'shish",    callback_data="adm_sub_add"),
         InlineKeyboardButton("🗑 Kanal o'chirish",   callback_data="adm_sub_del")],
        [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="adm_sub_list")],
        [InlineKeyboardButton("🔙 Orqaga",            callback_data="admin_panel")],
    ])

def sub_type_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Ommaviy kanal",     callback_data="sub_type_public")],
        [InlineKeyboardButton("🔒 Maxfiy kanal",      callback_data="sub_type_private")],
        [InlineKeyboardButton("✋ Zayavka (invite)",  callback_data="sub_type_invite")],
        [InlineKeyboardButton("🔙 Bekor qilish",      callback_data="adm_subs")],
    ])

def category_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Kino",          callback_data="cat_sel_movie"),
         InlineKeyboardButton("📺 Serial",         callback_data="cat_sel_serial")],
        [InlineKeyboardButton("🎌 Anime",          callback_data="cat_sel_anime"),
         InlineKeyboardButton("🎠 Multfilm",       callback_data="cat_sel_cartoon")],
        [InlineKeyboardButton("🎭 Drama",          callback_data="cat_sel_drama")],
        [InlineKeyboardButton("❌ Bekor qilish",   callback_data="admin_panel")],
    ])

def settings_kb():
    forward = get_setting("forward_enabled")
    fwd_text = "✅ Forward: Yoqilgan" if forward == "1" else "🚫 Forward: O'chirilgan"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(fwd_text, callback_data="adm_toggle_forward")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")],
    ])

def broadcast_kb(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "broadcast_fwd"),    callback_data="adm_bc_fwd")],
        [InlineKeyboardButton(t(lang, "broadcast_bot"),    callback_data="adm_bc_bot")],
        [InlineKeyboardButton(t(lang, "broadcast_single"), callback_data="adm_bc_single")],
        [InlineKeyboardButton("🔙 Orqaga",                  callback_data="admin_panel")],
    ])

# =====================
# ADMIN ROUTER
# =====================

async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    d = query.data
    lang = get_user_lang(uid)

    if not is_admin(uid):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return

    # === ADMIN PANEL ===
    if d == "admin_panel":
        await query.edit_message_text(
            t(lang, "admin_panel"),
            reply_markup=admin_menu_kb(lang),
            parse_mode="Markdown"
        )

    # === STATISTIKA ===
    elif d == "adm_stats":
        stats = get_stats()
        await query.edit_message_text(
            t(lang, "stats_msg", **stats),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]),
            parse_mode="Markdown"
        )

    # === OBUNA BOSHQARISH ===
    elif d == "adm_subs":
        await query.edit_message_text(
            "📢 *Majburiy obuna boshqaruvi:*",
            reply_markup=sub_menu_kb(),
            parse_mode="Markdown"
        )

    elif d == "adm_sub_list":
        subs = get_subscriptions()
        if not subs:
            text = "📋 Hozircha hech qanday kanal yo'q."
        else:
            text = "📋 *Kanallar ro'yxati:*\n\n"
            for i, s in enumerate(subs, 1):
                types = {"public": "📢 Ommaviy", "private": "🔒 Maxfiy", "invite": "✋ Zayavka"}
                text += f"{i}. {s['channel_name']} | {types.get(s['sub_type'], s['sub_type'])}\n"
                text += f"   ID: `{s['channel_id']}`\n\n"
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_subs")]]),
            parse_mode="Markdown"
        )

    elif d == "adm_sub_add":
        await query.edit_message_text(
            "📢 *Kanal turini tanlang:*",
            reply_markup=sub_type_kb(),
            parse_mode="Markdown"
        )

    elif d.startswith("sub_type_"):
        sub_type = d.replace("sub_type_", "")
        admin_states[uid] = {"step": "sub_channel_id", "sub_type": sub_type}
        type_names = {"public": "📢 Ommaviy", "private": "🔒 Maxfiy", "invite": "✋ Zayavka"}
        await query.edit_message_text(
            f"*{type_names[sub_type]}* tur tanlandi.\n\n"
            f"📝 Kanal ID yoki @username yuboring:\n"
            f"_Misol: @mening\\_kanalim yoki -1001234567890_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="adm_subs")]]),
            parse_mode="Markdown"
        )

    elif d == "adm_sub_del":
        subs = get_subscriptions()
        if not subs:
            await query.answer("Hech qanday kanal yo'q!", show_alert=True)
            return
        kb = []
        for s in subs:
            kb.append([InlineKeyboardButton(
                f"🗑 {s['channel_name']}",
                callback_data=f"del_sub_{s['id']}"
            )])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_subs")])
        await query.edit_message_text(
            "🗑 O'chirmoqchi bo'lgan kanalni tanlang:",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif d.startswith("del_sub_"):
        sub_id = int(d.replace("del_sub_", ""))
        remove_subscription(sub_id)
        await query.answer("✅ Kanal o'chirildi!", show_alert=True)
        subs = get_subscriptions()
        if not subs:
            await query.edit_message_text(
                "📢 *Majburiy obuna boshqaruvi:*",
                reply_markup=sub_menu_kb(),
                parse_mode="Markdown"
            )
        else:
            kb = []
            for s in subs:
                kb.append([InlineKeyboardButton(f"🗑 {s['channel_name']}", callback_data=f"del_sub_{s['id']}")])
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_subs")])
            await query.edit_message_text("🗑 O'chirmoqchi bo'lgan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(kb))

    # === KINO QO'SHISH ===
    elif d == "adm_add_movie":
        await query.edit_message_text(
            "🎬 *Kategoriyani tanlang:*",
            reply_markup=category_kb(),
            parse_mode="Markdown"
        )

    elif d.startswith("cat_sel_"):
        category = d.replace("cat_sel_", "")
        admin_states[uid] = {"step": "movie_title", "category": category, "data": {}}
        cat_names = {"movie": "🎬 Kino", "serial": "📺 Serial",
                     "anime": "🎌 Anime", "cartoon": "🎠 Multfilm", "drama": "🎭 Drama"}
        await query.edit_message_text(
            f"*{cat_names[category]}* tanlandi.\n\n📝 Kino nomini yozing (O'zbek tilda):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]]),
            parse_mode="Markdown"
        )

    # === KINO O'CHIRISH ===
    elif d == "adm_del_movie":
        admin_states[uid] = {"step": "del_movie_id"}
        await query.edit_message_text(
            "🗑 *O'chirmoqchi bo'lgan kino ID sini yozing:*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]]),
            parse_mode="Markdown"
        )

    # === XABAR YUBORISH ===
    elif d == "adm_broadcast":
        await query.edit_message_text(
            t(lang, "broadcast_type"),
            reply_markup=broadcast_kb(lang),
            parse_mode="Markdown"
        )

    elif d == "adm_bc_bot":
        admin_states[uid] = {"step": "broadcast_text", "bc_type": "bot"}
        await query.edit_message_text(
            "📣 Yubormoqchi bo'lgan xabarni yozing:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )

    elif d == "adm_bc_fwd":
        admin_states[uid] = {"step": "broadcast_fwd", "bc_type": "fwd"}
        await query.edit_message_text(
            "↩️ Forward qilmoqchi bo'lgan xabarni yuboring:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )

    elif d == "adm_bc_single":
        admin_states[uid] = {"step": "broadcast_user_id", "bc_type": "single"}
        await query.edit_message_text(
            t(lang, "enter_user_id"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )

    # === ADMIN QO'SHISH ===
    elif d == "adm_add_admin":
        admin_states[uid] = {"step": "add_admin_id"}
        await query.edit_message_text(
            "👤 Yangi admin Telegram ID sini yozing:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )

    # === VIP PANEL ===
    elif d == "adm_vip":
        admin_states[uid] = {"step": "vip_user_id"}
        await query.edit_message_text(
            "💎 *VIP panel:*\n\nVIP bermoqchi bo'lgan foydalanuvchi ID sini yozing:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]]),
            parse_mode="Markdown"
        )

    elif d.startswith("vip_give_"):
        parts = d.split("_")
        target_id = int(parts[2])
        days = int(parts[3])
        until = set_vip(target_id, days)
        await query.edit_message_text(
            f"✅ Foydalanuvchi {target_id} ga {days} kunlik VIP berildi!\nMuddati: {until}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )

    # === QO'SHIMCHA KANALLAR ===
    elif d == "adm_extra_channels":
        channels = get_extra_channels()
        text = "📡 *Qo'shimcha kanallar:*\n\n"
        if channels:
            for i, ch in enumerate(channels, 1):
                text += f"{i}. {ch['channel_name']} | `{ch['channel_id']}`\n"
        else:
            text += "_Hozircha kanal yo'q_"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Kanal qo'shish",   callback_data="adm_extra_add"),
             InlineKeyboardButton("🗑 Kanal o'chirish",  callback_data="adm_extra_del")],
            [InlineKeyboardButton("📤 Kanalga post tashlash", callback_data="adm_post_channels")],
            [InlineKeyboardButton("🔙 Orqaga",           callback_data="admin_panel")],
        ])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

    elif d == "adm_extra_add":
        admin_states[uid] = {"step": "extra_ch_id"}
        await query.edit_message_text(
            "📡 Kanal ID yoki @username yuboring:\n_Masalan: @mening\\_kanalim_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor", callback_data="adm_extra_channels")]]),
            parse_mode="Markdown"
        )

    elif d == "adm_extra_del":
        channels = get_extra_channels()
        if not channels:
            await query.answer("Hech qanday kanal yo'q!", show_alert=True)
            return
        kb = []
        for ch in channels:
            kb.append([InlineKeyboardButton(f"🗑 {ch['channel_name']}", callback_data=f"adm_extra_rm_{ch['id']}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_extra_channels")])
        await query.edit_message_text("🗑 O'chirmoqchi bo'lgan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("adm_extra_rm_"):
        ch_id = int(d.replace("adm_extra_rm_", ""))
        remove_extra_channel(ch_id)
        await query.answer("✅ Kanal o'chirildi!", show_alert=True)
        channels = get_extra_channels()
        if not channels:
            await query.edit_message_text(
                "📡 *Qo'shimcha kanallar:*\n\n_Hozircha kanal yo'q_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="adm_extra_add")],
                    [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]
                ]),
                parse_mode="Markdown"
            )
        else:
            kb = []
            for ch in channels:
                kb.append([InlineKeyboardButton(f"🗑 {ch['channel_name']}", callback_data=f"adm_extra_rm_{ch['id']}")])
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_extra_channels")])
            await query.edit_message_text("🗑 O'chirmoqchi bo'lgan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(kb))

    # === KANALGA POST TASHLASH ===
    elif d == "adm_post_channels":
        channels = get_extra_channels()
        if not channels:
            await query.answer("❌ Avval kanal qo'shing!", show_alert=True)
            return
        # Kanallarni tanlash (bir nechta)
        kb = []
        for ch in channels:
            kb.append([InlineKeyboardButton(
                f"☑️ {ch['channel_name']}",
                callback_data=f"adm_post_sel_{ch['id']}"
            )])
        kb.append([InlineKeyboardButton("✅ Barcha kanallarga", callback_data="adm_post_all")])
        kb.append([InlineKeyboardButton("🔙 Bekor", callback_data="adm_extra_channels")])
        admin_states[uid] = {"step": "post_select_channels", "selected": []}
        await query.edit_message_text(
            "📤 *Post tashlash:*\n\nKanallarni tanlang yoki barcha kanallarga yuboring:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

    elif d == "adm_post_all":
        channels = get_extra_channels()
        ch_ids = [ch["id"] for ch in channels]
        admin_states[uid] = {"step": "post_text", "selected": ch_ids, "links": []}
        await query.edit_message_text(
            "📝 Post matnini yozing:\n\n_Matn, rasm yoki video yuborishingiz mumkin_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor", callback_data="adm_extra_channels")]]),
            parse_mode="Markdown"
        )

    elif d.startswith("adm_post_sel_"):
        ch_id = int(d.replace("adm_post_sel_", ""))
        state = admin_states.get(uid, {"step": "post_select_channels", "selected": []})
        selected = state.get("selected", [])
        if ch_id in selected:
            selected.remove(ch_id)
        else:
            selected.append(ch_id)
        state["selected"] = selected
        admin_states[uid] = state

        channels = get_extra_channels()
        kb = []
        for ch in channels:
            mark = "✅" if ch["id"] in selected else "☑️"
            kb.append([InlineKeyboardButton(f"{mark} {ch['channel_name']}", callback_data=f"adm_post_sel_{ch['id']}")])
        kb.append([InlineKeyboardButton("✅ Barcha kanallarga", callback_data="adm_post_all")])
        if selected:
            kb.append([InlineKeyboardButton(f"➡️ Davom etish ({len(selected)} ta)", callback_data="adm_post_continue")])
        kb.append([InlineKeyboardButton("🔙 Bekor", callback_data="adm_extra_channels")])
        await query.edit_message_text(
            f"📤 *Post tashlash:*\n\nTanlangan: *{len(selected)} ta kanal*",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

    elif d == "adm_post_continue":
        state = admin_states.get(uid, {})
        state["step"] = "post_text"
        state["links"] = []
        admin_states[uid] = state
        await query.edit_message_text(
            "📝 Post matnini yozing:\n\n_Matn, rasm yoki video yuborishingiz mumkin_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor", callback_data="adm_extra_channels")]]),
            parse_mode="Markdown"
        )

    elif d == "adm_post_add_link":
        state = admin_states.get(uid, {})
        state["step"] = "post_add_link"
        admin_states[uid] = state
        links = state.get("links", [])
        await query.edit_message_text(
            f"🔗 Havola qo'shish ({len(links)}/20)\n\nFormat: `Matn | https://link.com`\n_Masalan: Bizning kanal | https://t.me/kanal_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="adm_post_send")]]),
            parse_mode="Markdown"
        )

    elif d == "adm_post_send":
        state = admin_states.get(uid, {})
        selected_ids = state.get("selected", [])
        post_data = state.get("post_data", {})
        links = state.get("links", [])

        if not post_data:
            await query.answer("❌ Post ma'lumoti topilmadi!", show_alert=True)
            return

        # Inline tugmalar (havola tugmalar)
        link_kb = None
        if links:
            link_buttons = []
            for link in links:
                parts = link.split("|")
                if len(parts) == 2:
                    link_buttons.append([InlineKeyboardButton(parts[0].strip(), url=parts[1].strip())])
            if link_buttons:
                link_kb = InlineKeyboardMarkup(link_buttons)

        # Tanlangan kanallarga yuborish
        all_channels = get_extra_channels()
        target_channels = [ch for ch in all_channels if ch["id"] in selected_ids]

        sent_names = []
        failed_names = []

        for ch in target_channels:
            try:
                if post_data.get("type") == "photo":
                    await context.bot.send_photo(
                        chat_id=ch["channel_id"],
                        photo=post_data["file_id"],
                        caption=post_data.get("text", ""),
                        reply_markup=link_kb,
                        parse_mode="Markdown"
                    )
                elif post_data.get("type") == "video":
                    await context.bot.send_video(
                        chat_id=ch["channel_id"],
                        video=post_data["file_id"],
                        caption=post_data.get("text", ""),
                        reply_markup=link_kb,
                        parse_mode="Markdown"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=ch["channel_id"],
                        text=post_data.get("text", ""),
                        reply_markup=link_kb,
                        parse_mode="Markdown"
                    )
                sent_names.append(ch["channel_name"])
            except Exception as e:
                failed_names.append(ch["channel_name"])

        # Saqlash
        save_post(uid, post_data.get("text", ""), str(links), str(sent_names))
        admin_states.pop(uid, None)

        result = f"✅ *Post yuborildi!*\n\n"
        result += f"✅ Muvaffaqiyatli: {len(sent_names)} ta\n"
        if sent_names:
            result += "\n".join([f"  • {n}" for n in sent_names]) + "\n"
        if failed_names:
            result += f"\n❌ Yuborilmadi: {len(failed_names)} ta\n"
            result += "\n".join([f"  • {n}" for n in failed_names])

        await query.edit_message_text(
            result,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin panel", callback_data="admin_panel")]]),
            parse_mode="Markdown"
        )

    elif d == "movie_vip_yes":
        state = admin_states.get(uid, {})
        state["data"]["is_vip"] = 1
        state["step"] = "movie_poster"
        admin_states[uid] = state
        await query.edit_message_text(
            "🖼 Poster rasmini yuboring:\n_(yoki — yozing o'tkazib yuborish uchun)_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="movie_skip_poster")]]),
            parse_mode="Markdown"
        )

    elif d == "movie_vip_no":
        state = admin_states.get(uid, {})
        state["data"]["is_vip"] = 0
        state["step"] = "movie_poster"
        admin_states[uid] = state
        await query.edit_message_text(
            "🖼 Poster rasmini yuboring:\n_(yoki o'tkazib yuborish uchun tugmani bosing)_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="movie_skip_poster")]]),
            parse_mode="Markdown"
        )

    elif d == "movie_skip_poster":
        state = admin_states.get(uid, {})
        state["data"]["poster_id"] = None
        state["data"]["added_by"] = uid
        category = state.get("category")
        if category in ("serial", "anime", "drama", "cartoon"):
            movie_id = add_movie(state["data"])
            admin_states.pop(uid, None)
            await query.edit_message_text(
                f"✅ *{state['data']['title']}* qo'shildi! (ID: `{movie_id}`)\n\n"
                f"Endi qismlarni qo'shishingiz mumkin:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Qism qo'shish", callback_data=f"adm_add_ep_{movie_id}")],
                    [InlineKeyboardButton("🔙 Admin panel", callback_data="admin_panel")]
                ]),
                parse_mode="Markdown"
            )
        else:
            # Kino — video fayl kerak
            admin_states[uid] = {"step": "add_ep_file", "movie_id": None,
                                  "season_id": None, "ep_num": 1,
                                  "pending_data": state["data"], "category": category}
            await query.edit_message_text(
                "🎬 Video faylni yuboring:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor", callback_data="admin_panel")]])
            )

    # === SOZLAMALAR ===
    elif d == "adm_settings":
        await query.edit_message_text(
            "⚙️ *Sozlamalar:*",
            reply_markup=settings_kb(),
            parse_mode="Markdown"
        )

    elif d == "adm_toggle_forward":
        current = get_setting("forward_enabled")
        new_val = "0" if current == "1" else "1"
        set_setting("forward_enabled", new_val)
        msg = "✅ Forward yoqildi!" if new_val == "1" else "🚫 Forward o'chirildi!"
        await query.answer(msg, show_alert=True)
        await query.edit_message_text(
            "⚙️ *Sozlamalar:*",
            reply_markup=settings_kb(),
            parse_mode="Markdown"
        )

    # === QISM QO'SHISH (serial/anime uchun) ===
    elif d.startswith("adm_add_ep_"):
        movie_id = int(d.replace("adm_add_ep_", ""))
        movie = get_movie(movie_id)
        if not movie:
            await query.answer("Kino topilmadi!", show_alert=True)
            return

        if movie["category"] in ("serial", "anime", "drama"):
            # Fasl tanlash
            seasons = get_seasons(movie_id)
            kb = []
            for s in seasons:
                kb.append([InlineKeyboardButton(
                    f"📂 {s['season_num']}-Fasl",
                    callback_data=f"adm_ep_season_{movie_id}_{s['id']}"
                )])
            kb.append([InlineKeyboardButton("➕ Yangi fasl qo'shish", callback_data=f"adm_new_season_{movie_id}")])
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
            await query.edit_message_text(
                f"📂 *{movie['title']}*\n\nFaslni tanlang yoki yangi fasl qo'shing:",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
        else:
            # Kino — to'g'ridan to'g'ri fayl
            admin_states[uid] = {"step": "add_ep_file", "movie_id": movie_id, "season_id": None, "ep_num": 1}
            await query.edit_message_text(
                f"🎬 *{movie['title']}*\n\nVideo faylni yuboring:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]]),
                parse_mode="Markdown"
            )

    elif d.startswith("adm_new_season_"):
        movie_id = int(d.replace("adm_new_season_", ""))
        admin_states[uid] = {"step": "new_season_num", "movie_id": movie_id}
        await query.edit_message_text(
            "📂 Yangi fasl raqamini yozing (masalan: 1, 2, 3):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )

    elif d.startswith("adm_ep_season_"):
        parts = d.split("_")
        movie_id = int(parts[3])
        season_id = int(parts[4])
        eps = get_episodes(movie_id, season_id)
        next_ep = len(eps) + 1
        admin_states[uid] = {"step": "add_ep_file", "movie_id": movie_id, "season_id": season_id, "ep_num": next_ep}
        movie = get_movie(movie_id)
        await query.edit_message_text(
            f"📺 *{movie['title']}*\n\n{next_ep}-qismni yuklang (video fayl):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]]),
            parse_mode="Markdown"
        )

# =====================
# MESSAGE HANDLER (ADMIN)
# =====================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return

    state = admin_states.get(uid, {})
    step = state.get("step", "")
    lang = get_user_lang(uid)
    text = update.message.text or ""

    # === KANAL QO'SHISH ===
    if step == "sub_channel_id":
        state["channel_id"] = text.strip()
        state["step"] = "sub_channel_name"
        admin_states[uid] = state
        await update.message.reply_text("📝 Kanal nomini yozing (ko'rinadigan nom):")

    elif step == "sub_channel_name":
        state["channel_name"] = text.strip()
        state["step"] = "sub_channel_url"
        admin_states[uid] = state
        sub_type = state.get("sub_type")
        if sub_type == "public":
            await update.message.reply_text("🔗 Kanal linkini yozing (@username yoki https://t.me/...):")
        elif sub_type == "private":
            await update.message.reply_text("🔗 Invite linkni yozing (https://t.me/+...):")
        else:
            await update.message.reply_text("🔗 Kanal linkini yozing:")

    elif step == "sub_channel_url":
        state["channel_url"] = text.strip()
        state["step"] = "sub_min_members"
        admin_states[uid] = state
        await update.message.reply_text(
            "👥 Minimal obunachi soni kiriting:\n"
            "_0 kiritsangiz — tekshirilmaydi_",
            parse_mode="Markdown"
        )

    elif step == "sub_min_members":
        try:
            min_m = int(text.strip())
        except:
            min_m = 0
        add_subscription(
            state["channel_id"], state["channel_name"],
            state["channel_url"], state["sub_type"], min_m
        )
        admin_states.pop(uid, None)
        await update.message.reply_text(
            f"✅ *{state['channel_name']}* kanali qo'shildi!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Obuna menyu", callback_data="adm_subs")]]),
            parse_mode="Markdown"
        )

    # === KINO QO'SHISH ===
    elif step == "movie_title":
        state["data"]["title"] = text.strip()
        state["step"] = "movie_title_ru"
        admin_states[uid] = state
        await update.message.reply_text("📝 Kino nomini rus tilida yozing (yoki — yozing o'tkazib yuborish uchun):")

    elif step == "movie_title_ru":
        state["data"]["title_ru"] = None if text.strip() == "—" else text.strip()
        state["step"] = "movie_year"
        admin_states[uid] = state
        await update.message.reply_text("📅 Yilni yozing (masalan: 2023):")

    elif step == "movie_year":
        try:
            state["data"]["year"] = int(text.strip())
        except:
            state["data"]["year"] = None
        state["step"] = "movie_country"
        admin_states[uid] = state
        await update.message.reply_text("🌍 Mamlakatni yozing:")

    elif step == "movie_country":
        state["data"]["country"] = text.strip()
        state["step"] = "movie_genre"
        admin_states[uid] = state
        await update.message.reply_text("🎭 Janrni yozing (masalan: Drama, Komediya):")

    elif step == "movie_genre":
        state["data"]["genre"] = text.strip()
        state["step"] = "movie_desc"
        admin_states[uid] = state
        await update.message.reply_text("📖 Tavsif yozing (o'zbek tilda):")

    elif step == "movie_desc":
        state["data"]["description"] = text.strip()
        state["step"] = "movie_desc_ru"
        admin_states[uid] = state
        await update.message.reply_text("📖 Tavsif rus tilida (yoki — yozing):")

    elif step == "movie_desc_ru":
        state["data"]["desc_ru"] = None if text.strip() == "—" else text.strip()
        state["step"] = "movie_vip"
        admin_states[uid] = state
        await update.message.reply_text(
            "💎 VIP kino bo'ladimi?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ha, VIP", callback_data="movie_vip_yes"),
                 InlineKeyboardButton("❌ Yo'q", callback_data="movie_vip_no")]
            ])
        )

    elif step == "movie_poster":
        # Poster rasm kelsa
        if update.message.photo:
            photo_id = update.message.photo[-1].file_id
            state["data"]["poster_id"] = photo_id
        state["data"]["added_by"] = uid
        state["step"] = "movie_file"
        admin_states[uid] = state

        category = state.get("category")
        if category in ("serial", "anime", "drama"):
            movie_id = add_movie(state["data"])
            admin_states.pop(uid, None)
            await update.message.reply_text(
                f"✅ *{state['data']['title']}* qo'shildi! (ID: {movie_id})\n\n"
                f"Endi qismlarni qo'shishingiz mumkin:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Qism qo'shish", callback_data=f"adm_add_ep_{movie_id}")],
                    [InlineKeyboardButton("🔙 Admin panel", callback_data="admin_panel")]
                ]),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("🎬 Video faylni yuboring:")

    # === VIDEO FAYL (kino yoki qism) ===
    elif step == "add_ep_file":
        if update.message.video or update.message.document:
            file_id = (update.message.video or update.message.document).file_id

            # Agar kino yangi qo'shilayotgan bo'lsa (pending_data)
            if state.get("pending_data") and not state.get("movie_id"):
                data = state["pending_data"]
                data["added_by"] = uid
                movie_id = add_movie(data)
                state["movie_id"] = movie_id

            movie_id = state["movie_id"]
            season_id = state.get("season_id")
            ep_num = state.get("ep_num", 1)

            # Storage kanalga yuborish
            try:
                await context.bot.forward_message(
                    chat_id=STORAGE_CHANNEL_ID,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
            except:
                pass

            add_episode(movie_id, file_id, season_id, ep_num)
            movie = get_movie(movie_id)

            await update.message.reply_text(
                f"✅ {ep_num}-qism qo'shildi!\n\n*{movie['title']}* (ID: `{movie_id}`)\n\n"
                f"Yana qism qo'shishni xohlaysizmi?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Yana qism qo'shish", callback_data=f"adm_add_ep_{movie_id}")],
                    [InlineKeyboardButton("✅ Tugallash", callback_data="admin_panel")]
                ]),
                parse_mode="Markdown"
            )
            admin_states.pop(uid, None)
        else:
            await update.message.reply_text("❌ Iltimos, video fayl yuboring!")

    # === KINO O'CHIRISH ===
    elif step == "del_movie_id":
        try:
            movie_id = int(text.strip())
            movie = get_movie(movie_id)
            if movie:
                delete_movie(movie_id)
                delete_episodes(movie_id)
                await update.message.reply_text(
                    f"✅ *{movie['title']}* o'chirildi!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin panel", callback_data="admin_panel")]]),
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Kino topilmadi!")
        except:
            await update.message.reply_text("❌ Noto'g'ri ID!")
        admin_states.pop(uid, None)

    # === YANGI FASL ===
    elif step == "new_season_num":
        try:
            season_num = int(text.strip())
            movie_id = state["movie_id"]
            season_id = add_season(movie_id, season_num)
            admin_states[uid] = {"step": "add_ep_file", "movie_id": movie_id, "season_id": season_id, "ep_num": 1}
            await update.message.reply_text(
                f"✅ {season_num}-fasl yaratildi!\n\n1-qismni video fayl sifatida yuboring:"
            )
        except:
            await update.message.reply_text("❌ Raqam kiriting!")

    # === XABAR YUBORISH ===
    elif step == "broadcast_text":
        users = get_all_users()
        sent = 0
        for user_id in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
                sent += 1
            except:
                pass
        admin_states.pop(uid, None)
        await update.message.reply_text(
            t(lang, "broadcast_sent", count=sent),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin panel", callback_data="admin_panel")]])
        )

    elif step == "broadcast_fwd":
        users = get_all_users()
        sent = 0
        for user_id in users:
            try:
                await context.bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                sent += 1
            except:
                pass
        admin_states.pop(uid, None)
        await update.message.reply_text(t(lang, "broadcast_sent", count=sent))

    elif step == "broadcast_user_id":
        try:
            target_id = int(text.strip())
            state["target_id"] = target_id
            state["step"] = "broadcast_single_text"
            admin_states[uid] = state
            await update.message.reply_text("📝 Xabarni yozing:")
        except:
            await update.message.reply_text("❌ Noto'g'ri ID!")

    elif step == "broadcast_single_text":
        target_id = state["target_id"]
        try:
            await context.bot.send_message(chat_id=target_id, text=text)
            await update.message.reply_text("✅ Xabar yuborildi!")
        except:
            await update.message.reply_text("❌ Xabar yuborib bo'lmadi!")
        admin_states.pop(uid, None)

    # === ADMIN QO'SHISH ===
    elif step == "add_admin_id":
        try:
            new_admin_id = int(text.strip())
            add_admin(new_admin_id, uid)
            await update.message.reply_text(
                f"✅ {new_admin_id} admin qilindi!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin panel", callback_data="admin_panel")]])
            )
        except:
            await update.message.reply_text("❌ Noto'g'ri ID!")
        admin_states.pop(uid, None)

    # === VIP BERISH ===
    elif step == "vip_user_id":
        try:
            target_id = int(text.strip())
            state["vip_target"] = target_id
            state["step"] = "vip_days"
            admin_states[uid] = state
            await update.message.reply_text(
                f"💎 {target_id} foydalanuvchiga necha kunlik VIP?\n\nTez tanlash:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("30 kun", callback_data=f"vip_give_{target_id}_30"),
                     InlineKeyboardButton("90 kun", callback_data=f"vip_give_{target_id}_90")],
                    [InlineKeyboardButton("365 kun", callback_data=f"vip_give_{target_id}_365")],
                    [InlineKeyboardButton("❌ Bekor", callback_data="admin_panel")]
                ])
            )
        except:
            await update.message.reply_text("❌ Noto'g'ri ID!")
            admin_states.pop(uid, None)

    # === QO'SHIMCHA KANAL ID ===
    elif step == "extra_ch_id":
        state["extra_ch_id"] = text.strip()
        state["step"] = "extra_ch_name"
        admin_states[uid] = state
        await update.message.reply_text("📝 Kanal nomini yozing (ko'rinadigan nom):")

    elif step == "extra_ch_name":
        ch_id = state["extra_ch_id"]
        ch_name = text.strip()
        add_extra_channel(ch_id, ch_name)
        admin_states.pop(uid, None)
        await update.message.reply_text(
            f"✅ *{ch_name}* qo'shimcha kanal sifatida qo'shildi!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📡 Kanallar", callback_data="adm_extra_channels")]]),
            parse_mode="Markdown"
        )

    # === POST MATNI YOKI MEDIA ===
    elif step == "post_text":
        post_data = {}
        if update.message.photo:
            post_data["type"] = "photo"
            post_data["file_id"] = update.message.photo[-1].file_id
            post_data["text"] = update.message.caption or ""
        elif update.message.video:
            post_data["type"] = "video"
            post_data["file_id"] = update.message.video.file_id
            post_data["text"] = update.message.caption or ""
        else:
            post_data["type"] = "text"
            post_data["text"] = text

        state["post_data"] = post_data
        state["step"] = "post_links"
        admin_states[uid] = state

        await update.message.reply_text(
            f"✅ Post tayyor!\n\n"
            f"📎 Havola (link) tugmalar qo'shmoqchimisiz? (1-20 ta)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Havola qo'shish", callback_data="adm_post_add_link")],
                [InlineKeyboardButton("📤 Hoziroq yuborish", callback_data="adm_post_send")],
                [InlineKeyboardButton("❌ Bekor", callback_data="adm_extra_channels")]
            ])
        )

    # === POST HAVOLASI ===
    elif step == "post_add_link":
        links = state.get("links", [])
        if "|" in text:
            links.append(text.strip())
            state["links"] = links
            admin_states[uid] = state
            await update.message.reply_text(
                f"✅ Havola qo'shildi! ({len(links)}/20)\n\n"
                f"Yana havola qo'shish yoki yuborish:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Yana havola", callback_data="adm_post_add_link")] if len(links) < 20 else [],
                    [InlineKeyboardButton("📤 Yuborish", callback_data="adm_post_send")],
                    [InlineKeyboardButton("❌ Bekor", callback_data="adm_extra_channels")]
                ])
            )
        else:
            await update.message.reply_text(
                "❌ Format noto'g'ri!\n\n"
                "Format: `Tugma nomi | https://link.com`\n"
                "_Masalan: Bizning kanal | https://t.me/kanal_",
                parse_mode="Markdown"
            )
