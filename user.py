from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import *
from languages import t
from config import VIP_PRICES

user_states = {}

CATEGORIES = {
    "movie":   "🎬 Kinolar",
    "serial":  "📺 Seriallar",
    "anime":   "🎌 Anime",
    "cartoon": "🎠 Multfilmlar",
    "drama":   "🎭 Dramalar",
}

# =====================
# YORDAMCHI FUNKSIYALAR
# =====================

def movie_kb(movie, lang, uid):
    fav = "❤️" if get_favorites(uid) else "🤍"
    kb = [
        [InlineKeyboardButton("▶️ Ko'rish / Yuklab olish", callback_data=f"watch_{movie['id']}")],
        [InlineKeyboardButton(f"{fav} Sevimli", callback_data=f"fav_{movie['id']}"),
         InlineKeyboardButton("🕐 Keyinroq", callback_data=f"later_{movie['id']}")],
        [InlineKeyboardButton("⭐ Baho berish", callback_data=f"rate_{movie['id']}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data=f"cat_{movie['category']}")],
    ]
    return InlineKeyboardMarkup(kb)

def movie_text(movie, lang):
    vip_badge = "💎 VIP | " if movie["is_vip"] else ""
    return t(lang, "movie_info",
             title=movie["title"],
             year=movie["year"] or "—",
             rating=movie["rating"] or "—",
             country=movie["country"] or "—",
             genre=movie["genre"] or "—",
             description=movie["description"] or "—"
             ).replace("{vip}", vip_badge)

def movies_list_kb(movies, category, lang, page=0, per_page=8):
    kb = []
    row = []
    for i, m in enumerate(movies):
        vip = "💎 " if m["is_vip"] else ""
        btn = InlineKeyboardButton(f"{vip}{m['title']}", callback_data=f"movie_{m['id']}")
        row.append(btn)
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)

    # Sahifalash
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"page_{category}_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}", callback_data="noop"))
    kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

# =====================
# USER ROUTER
# =====================

async def user_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    d = query.data
    lang = get_user_lang(uid)

    # === KATEGORIYA ===
    if d.startswith("cat_"):
        category = d.replace("cat_", "")
        movies = get_movies_by_category(category)
        if not movies:
            await query.edit_message_text(
                f"{CATEGORIES.get(category, category)}\n\n❌ Hozircha kino yo'q.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]])
            )
            return
        await query.edit_message_text(
            f"{CATEGORIES.get(category, category)} — *{len(movies)} ta*",
            reply_markup=movies_list_kb(movies, category, lang),
            parse_mode="Markdown"
        )

    # === SAHIFALASH ===
    elif d.startswith("page_"):
        parts = d.split("_")
        category = parts[1]
        page = int(parts[2])
        per_page = 8
        movies = get_movies_by_category(category, limit=per_page, offset=page*per_page)
        await query.edit_message_text(
            f"{CATEGORIES.get(category, category)}",
            reply_markup=movies_list_kb(movies, category, lang, page),
            parse_mode="Markdown"
        )

    # === KINO KARTOCHKASI ===
    elif d.startswith("movie_"):
        movie_id = int(d.replace("movie_", ""))
        movie = get_movie(movie_id)
        if not movie:
            await query.answer("❌ Kino topilmadi!", show_alert=True)
            return

        # VIP tekshirish
        if movie["is_vip"] and not is_vip(uid):
            await query.edit_message_text(
                t(lang, "vip_only"),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 VIP olish", callback_data="vip")],
                    [InlineKeyboardButton("🔙 Orqaga", callback_data=f"cat_{movie['category']}")]
                ])
            )
            return

        add_view(uid, movie_id)
        text = movie_text(movie, lang)

        if movie["poster_id"]:
            try:
                await query.message.reply_photo(
                    photo=movie["poster_id"],
                    caption=text,
                    reply_markup=movie_kb(movie, lang, uid),
                    parse_mode="Markdown"
                )
                await query.message.delete()
                return
            except:
                pass

        await query.edit_message_text(
            text,
            reply_markup=movie_kb(movie, lang, uid),
            parse_mode="Markdown"
        )

    # === KO'RISH (fayl yuborish) ===
    elif d.startswith("watch_"):
        movie_id = int(d.replace("watch_", ""))
        movie = get_movie(movie_id)
        if not movie:
            await query.answer("❌ Topilmadi!", show_alert=True)
            return

        forward_enabled = get_setting("forward_enabled") == "1"
        category = movie["category"]

        if category in ("serial", "anime", "drama"):
            # Fasllar menyusi
            seasons = get_seasons(movie_id)
            if seasons:
                kb = []
                for s in seasons:
                    eps = get_episodes(movie_id, s["id"])
                    kb.append([InlineKeyboardButton(
                        f"📂 {s['season_num']}-Fasl ({len(eps)} qism)",
                        callback_data=f"season_{movie_id}_{s['id']}"
                    )])
                kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"movie_{movie_id}")])
                await query.edit_message_text(
                    f"📂 *{movie['title']}*\n\nFaslni tanlang:",
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode="Markdown"
                )
            else:
                # Faslsiz qismlar
                eps = get_episodes(movie_id)
                await send_episodes(query, eps, movie, lang, forward_enabled)

        else:
            # Kino — bitta fayl
            eps = get_episodes(movie_id)
            if eps:
                ep = eps[0]
                try:
                    if forward_enabled:
                        await context.bot.send_video(
                            chat_id=uid,
                            video=ep["file_id"],
                            caption=f"🎬 *{movie['title']}*",
                            parse_mode="Markdown"
                        )
                    else:
                        await context.bot.forward_message(
                            chat_id=uid,
                            from_chat_id=ep["file_id"],
                            message_id=ep["file_id"]
                        )
                    await query.answer("✅ Yuborildi!", show_alert=False)
                except Exception as e:
                    await query.answer("❌ Xatolik!", show_alert=True)
            else:
                await query.answer("❌ Fayl topilmadi!", show_alert=True)

    # === FASL QISMLARI ===
    elif d.startswith("season_"):
        parts = d.split("_")
        movie_id = int(parts[1])
        season_id = int(parts[2])
        movie = get_movie(movie_id)
        eps = get_episodes(movie_id, season_id)

        kb = []
        row = []
        for ep in eps:
            ep_type = "🎬" if ep["ep_type"] == "movie" else ("🌟" if ep["ep_type"] == "ova" else "📺")
            btn = InlineKeyboardButton(
                f"{ep_type} {ep['episode_num']}-qism",
                callback_data=f"ep_{ep['id']}"
            )
            row.append(btn)
            if len(row) == 3:
                kb.append(row)
                row = []
        if row:
            kb.append(row)

        # Barcha qismlar
        kb.append([InlineKeyboardButton("⬇️ Barcha qismlar", callback_data=f"all_eps_{movie_id}_{season_id}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"watch_{movie_id}")])

        await query.edit_message_text(
            f"📺 *{movie['title']}*\n\nQismni tanlang:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

    # === ALOHIDA QISM ===
    elif d.startswith("ep_"):
        ep_id = int(d.replace("ep_", ""))
        from database import get_conn
        conn = get_conn()
        ep = conn.execute("SELECT * FROM episodes WHERE id=?", (ep_id,)).fetchone()
        conn.close()
        if ep:
            try:
                await context.bot.send_video(
                    chat_id=uid,
                    video=ep["file_id"],
                    caption=f"📺 {ep['episode_num']}-qism",
                    parse_mode="Markdown"
                )
                await query.answer("✅ Yuborildi!")
            except:
                await query.answer("❌ Xatolik!", show_alert=True)
        else:
            await query.answer("❌ Topilmadi!", show_alert=True)

    # === BARCHA QISMLAR ===
    elif d.startswith("all_eps_"):
        parts = d.split("_")
        movie_id = int(parts[2])
        season_id = int(parts[3])
        eps = get_episodes(movie_id, season_id)
        movie = get_movie(movie_id)
        await query.answer(f"⬇️ {len(eps)} ta qism yuborilmoqda...", show_alert=False)
        for ep in eps:
            try:
                await context.bot.send_video(
                    chat_id=uid,
                    video=ep["file_id"],
                    caption=f"📺 {ep['episode_num']}-qism | {movie['title']}"
                )
            except:
                pass

    # === SEVIMLILAR ===
    elif d.startswith("fav_"):
        movie_id = int(d.replace("fav_", ""))
        added = toggle_favorite(uid, movie_id)
        if added:
            await query.answer(t(lang, "add_favorite"), show_alert=True)
        else:
            await query.answer("💔 Sevimlilardan olib tashlandi!", show_alert=True)

    elif d == "favorites":
        movies = get_favorites(uid)
        if not movies:
            await query.edit_message_text(
                "❤️ *Sevimlilar bo'sh*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]),
                parse_mode="Markdown"
            )
            return
        await query.edit_message_text(
            f"❤️ *Sevimlilar* — {len(movies)} ta",
            reply_markup=movies_list_kb(movies, "fav", lang),
            parse_mode="Markdown"
        )

    # === KEYINROQ KO'RAMAN ===
    elif d.startswith("later_"):
        movie_id = int(d.replace("later_", ""))
        added = toggle_watch_later(uid, movie_id)
        if added:
            await query.answer(t(lang, "add_watchlater"), show_alert=True)
        else:
            await query.answer("🗑 Keyinroq ko'ramanlardan olib tashlandi!", show_alert=True)

    elif d == "watch_later":
        movies = get_watch_later(uid)
        if not movies:
            await query.edit_message_text(
                "🕐 *Keyinroq ko'raman bo'sh*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]),
                parse_mode="Markdown"
            )
            return
        await query.edit_message_text(
            f"🕐 *Keyinroq ko'raman* — {len(movies)} ta",
            reply_markup=movies_list_kb(movies, "later", lang),
            parse_mode="Markdown"
        )

    # === BAHO BERISH ===
    elif d.startswith("rate_"):
        movie_id = int(d.replace("rate_", ""))
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("⭐1", callback_data=f"setrate_{movie_id}_1"),
            InlineKeyboardButton("⭐2", callback_data=f"setrate_{movie_id}_2"),
            InlineKeyboardButton("⭐3", callback_data=f"setrate_{movie_id}_3"),
            InlineKeyboardButton("⭐4", callback_data=f"setrate_{movie_id}_4"),
            InlineKeyboardButton("⭐5", callback_data=f"setrate_{movie_id}_5"),
        ], [InlineKeyboardButton("🔙 Orqaga", callback_data=f"movie_{movie_id}")]])
        await query.edit_message_text("⭐ Baho bering (1 dan 5 gacha):", reply_markup=kb)

    elif d.startswith("setrate_"):
        parts = d.split("_")
        movie_id = int(parts[1])
        rating = int(parts[2])
        set_rating(uid, movie_id, rating)
        await query.answer(t(lang, "rated"), show_alert=True)
        movie = get_movie(movie_id)
        await query.edit_message_text(
            movie_text(movie, lang),
            reply_markup=movie_kb(movie, lang, uid),
            parse_mode="Markdown"
        )

    # === TASODIFIY ===
    elif d == "random":
        movie = get_random_movie()
        if not movie:
            await query.answer("❌ Hech qanday kino yo'q!", show_alert=True)
            return
        if movie["is_vip"] and not is_vip(uid):
            movie = get_random_movie()
        add_view(uid, movie["id"])
        await query.edit_message_text(
            movie_text(movie, lang),
            reply_markup=movie_kb(movie, lang, uid),
            parse_mode="Markdown"
        )

    # === QIDIRUV ===
    elif d == "search":
        user_states[uid] = "searching"
        await query.edit_message_text(
            t(lang, "search_prompt"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]])
        )

    # === VIP ===
    elif d == "vip":
        if is_vip(uid):
            row = get_user(uid)
            await query.edit_message_text(
                t(lang, "vip_active", date=row["vip_until"]),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]),
                parse_mode="Markdown"
            )
        else:
            from config import VIP_STARS
            await query.edit_message_text(
                f"💎 *VIP obuna*\n\n"
                f"✅ Barcha VIP kinolarga kirish\n"
                f"✅ Reklamasiz ko'rish\n"
                f"✅ Birinchi bo'lib yangi kontentlar\n\n"
                f"💳 *Telegram Stars bilan to'lang:*\n\n"
                f"⭐ 1 oy — {VIP_STARS['1_oy']['stars']} Stars\n"
                f"⭐ 3 oy — {VIP_STARS['3_oy']['stars']} Stars\n"
                f"⭐ 12 oy — {VIP_STARS['12_oy']['stars']} Stars",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"⭐ 1 oy — {VIP_STARS['1_oy']['stars']} Stars",  callback_data="stars_1_oy")],
                    [InlineKeyboardButton(f"⭐ 3 oy — {VIP_STARS['3_oy']['stars']} Stars",  callback_data="stars_3_oy")],
                    [InlineKeyboardButton(f"⭐ 12 oy — {VIP_STARS['12_oy']['stars']} Stars", callback_data="stars_12_oy")],
                    [InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]
                ]),
                parse_mode="Markdown"
            )

    # === PROFIL ===
    elif d == "profile":
        row = get_user(uid)
        vip_status = t(lang, "vip_active", date=row["vip_until"]) if is_vip(uid) else "❌ Yo'q"
        await query.edit_message_text(
            t(lang, "profile_msg",
              id=uid,
              name=row["full_name"] or "—",
              date=row["joined_at"][:10],
              views=row["views"],
              vip=vip_status),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📩 Admin bilan bog'lanish", callback_data="contact_admin")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]
            ]),
            parse_mode="Markdown"
        )

    # === ADMIN BILAN BOG'LANISH ===
    elif d == "contact_admin":
        user_states[uid] = "contact_admin"
        await query.edit_message_text(
            "📩 *Admin bilan bog'lanish*\n\n"
            "Xabaringizni yozing, admin ko'rib chiqadi:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor qilish", callback_data="profile")
            ]]),
            parse_mode="Markdown"
        )

    # === ADMIN JAVOB BERISH ===
    elif d.startswith("reply_to_"):
        target_id = int(d.replace("reply_to_", ""))
        user_states[uid] = f"admin_reply_{target_id}"
        await query.message.reply_text(
            f"✏️ {target_id} foydalanuvchiga javob yozing:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")
            ]])
        )

    elif d == "noop":
        await query.answer()

    # === STARS TO'LOV ===
    elif d.startswith("stars_"):
        from bot import stars_invoice
        await stars_invoice(update, context)

async def send_episodes(query, eps, movie, lang, forward_enabled):
    kb = []
    row = []
    for ep in eps:
        btn = InlineKeyboardButton(f"📺 {ep['episode_num']}", callback_data=f"ep_{ep['id']}")
        row.append(btn)
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("⬇️ Barchasi", callback_data=f"all_eps_{movie['id']}_0")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"movie_{movie['id']}")])
    await query.edit_message_text(
        f"📺 *{movie['title']}*\n\nQismni tanlang ({len(eps)} ta):",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# =====================
# MESSAGE HANDLER (USER)
# =====================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text or ""
    lang = get_user_lang(uid)
    state = user_states.get(uid, "")

    # === ADMIN BILAN BOG'LANISH ===
    if state == "contact_admin":
        from config import ADMIN_IDS
        user_states.pop(uid, None)
        row = get_user(uid)
        name = row["full_name"] or "Noma'lum"

        # Adminga xabar yuborish
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📩 *Yangi xabar!*\n\n"
                         f"👤 Foydalanuvchi: [{name}](tg://user?id={uid})\n"
                         f"🆔 ID: `{uid}`\n\n"
                         f"💬 Xabar:\n{text}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Javob berish", callback_data=f"reply_to_{uid}")
                    ]]),
                    parse_mode="Markdown"
                )
            except:
                pass

        await update.message.reply_text(
            "✅ *Xabaringiz adminga yuborildi!*\n\n"
            "Tez orada javob berishadi 😊",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu")
            ]]),
            parse_mode="Markdown"
        )
        return

    # === ADMIN JAVOB BERISHI ===
    if state and state.startswith("admin_reply_"):
        target_id = int(state.replace("admin_reply_", ""))
        user_states.pop(uid, None)
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"📬 *Admin javob berdi:*\n\n{text}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📩 Javob berish", callback_data="contact_admin")
                ]]),
                parse_mode="Markdown"
            )
            await update.message.reply_text(
                "✅ Javobingiz yuborildi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Admin panel", callback_data="admin_panel")
                ]])
            )
        except:
            await update.message.reply_text("❌ Xabar yuborib bo'lmadi!")
        return

    # Qidiruv
    if state == "searching":
        results = search_movies(text)
        user_states.pop(uid, None)
        if not results:
            await update.message.reply_text(
                t(lang, "no_results"),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]])
            )
            return
        await update.message.reply_text(
            f"🔍 *{len(results)} ta natija topildi:*",
            reply_markup=movies_list_kb(results, "search", lang),
            parse_mode="Markdown"
        )

    elif text.startswith("/movie_"):
        try:
            movie_id = int(text.replace("/movie_", ""))
            movie = get_movie(movie_id)
            if movie:
                add_view(uid, movie_id)
                from telegram import InlineKeyboardMarkup
                await update.message.reply_text(
                    movie_text(movie, lang),
                    reply_markup=movie_kb(movie, lang, uid),
                    parse_mode="Markdown"
                )
        except:
            pass
    else:
        from database import is_admin
        if not is_admin(uid):
            await update.message.reply_text(
                "Menyu uchun /start bosing! 😊",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu")]])
            )
