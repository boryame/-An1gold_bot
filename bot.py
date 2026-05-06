import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest, LabeledPrice
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                           CallbackQueryHandler, InlineQueryHandler,
                           ChatJoinRequestHandler, PreCheckoutQueryHandler,
                           filters, ContextTypes)
from config import BOT_TOKEN, ADMIN_IDS, VIP_STARS
from database import init_db, add_user, get_user, get_user_lang, is_admin, get_subscriptions
from languages import t
from user import user_router
from admin import admin_router
from subscription import check_subscription

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# =====================
# KLAVIATURALAR
# =====================

def main_menu_kb(lang, is_adm=False):
    kb = [
        [InlineKeyboardButton(t(lang, "movies"),   callback_data="cat_movie"),
         InlineKeyboardButton(t(lang, "serials"),  callback_data="cat_serial")],
        [InlineKeyboardButton(t(lang, "anime"),    callback_data="cat_anime"),
         InlineKeyboardButton(t(lang, "cartoons"), callback_data="cat_cartoon")],
        [InlineKeyboardButton(t(lang, "drama"),    callback_data="cat_drama"),
         InlineKeyboardButton(t(lang, "random"),   callback_data="random")],
        [InlineKeyboardButton(t(lang, "search"),   callback_data="search"),
         InlineKeyboardButton(t(lang, "vip"),      callback_data="vip")],
        [InlineKeyboardButton(t(lang, "favorites"),    callback_data="favorites"),
         InlineKeyboardButton(t(lang, "watch_later"),  callback_data="watch_later")],
        [InlineKeyboardButton("📩 Admin bilan bog'lanish", callback_data="contact_admin"),
         InlineKeyboardButton(t(lang, "lang_btn"),  callback_data="lang")],
    ]
    if is_adm:
        kb.append([InlineKeyboardButton("👑 Admin panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

def lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="set_lang_uz"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru")]
    ])

# =====================
# START
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.full_name, user.username)

    # Super admin tekshirish
    if user.id in ADMIN_IDS:
        from database import add_admin
        add_admin(user.id, user.id)

    lang = get_user_lang(user.id)

    # Til tanlash (birinchi marta)
    db_user = get_user(user.id)
    if not db_user or db_user["lang"] == "uz":
        # Til so'rash
        await update.message.reply_text(
            "🌐 Tilni tanlang / Выберите язык:",
            reply_markup=lang_kb()
        )
        return

    # Majburiy obuna tekshirish
    not_subbed = await check_subscription(user.id, context)
    if not_subbed:
        await show_subscription(update, context, not_subbed, lang)
        return

    adm = is_admin(user.id)
    await update.message.reply_text(
        t(lang, "start_msg"),
        reply_markup=main_menu_kb(lang, adm),
        parse_mode="Markdown"
    )

async def show_subscription(update_or_query, context, channels, lang):
    kb = []
    for ch in channels:
        kb.append([InlineKeyboardButton(
            f"📢 {ch['channel_name']}",
            url=ch["channel_url"]
        )])
    kb.append([InlineKeyboardButton(t(lang, "sub_check"), callback_data="check_sub")])

    text = t(lang, "sub_required")
    if hasattr(update_or_query, "message"):
        await update_or_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update_or_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

# =====================
# CALLBACK HANDLER
# =====================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    d = query.data
    lang = get_user_lang(uid)

    # Til o'rnatish
    if d.startswith("set_lang_"):
        new_lang = d.replace("set_lang_", "")
        from database import set_user_lang
        set_user_lang(uid, new_lang)
        lang = new_lang

        # Obuna tekshirish
        not_subbed = await check_subscription(uid, context)
        if not_subbed:
            await show_subscription(query, context, not_subbed, lang)
            return

        adm = is_admin(uid)
        await query.edit_message_text(
            t(lang, "start_msg"),
            reply_markup=main_menu_kb(lang, adm),
            parse_mode="Markdown"
        )
        return

    # Til o'zgartirish
    if d == "lang":
        await query.edit_message_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=lang_kb())
        return

    # Bosh menyu
    if d == "menu":
        not_subbed = await check_subscription(uid, context)
        if not_subbed:
            await show_subscription(query, context, not_subbed, lang)
            return
        adm = is_admin(uid)
        await query.edit_message_text(
            t(lang, "start_msg"),
            reply_markup=main_menu_kb(lang, adm),
            parse_mode="Markdown"
        )
        return

    # Obunani tekshirish
    if d == "check_sub":
        not_subbed = await check_subscription(uid, context)
        if not_subbed:
            await query.answer(t(lang, "sub_fail"), show_alert=True)
            await show_subscription(query, context, not_subbed, lang)
        else:
            await query.answer(t(lang, "sub_ok"), show_alert=True)
            adm = is_admin(uid)
            await query.edit_message_text(
                t(lang, "start_msg"),
                reply_markup=main_menu_kb(lang, adm),
                parse_mode="Markdown"
            )
        return

    # Admin panel va barcha admin callbacklar
    if is_admin(uid) and (
        d == "admin_panel" or
        d.startswith("adm_") or
        d.startswith("sub_type_") or
        d.startswith("del_sub_") or
        d.startswith("cat_sel_") or
        d.startswith("adm_ep_") or
        d.startswith("adm_new_season_") or
        d.startswith("adm_add_ep_") or
        d.startswith("vip_give_") or
        d.startswith("adm_bc_") or
        d.startswith("reply_to_") or
        d in ("movie_vip_yes", "movie_vip_no", "movie_skip_poster")
    ):
        await admin_router(update, context)
        return

    # Qolganlarini user_router ga yuborish
    await user_router(update, context)

# =====================
# TELEGRAM STARS TO'LOV
# =====================

async def stars_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stars orqali VIP sotib olish"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    lang = get_user_lang(uid)
    d = query.data  # stars_1_oy, stars_3_oy, stars_12_oy

    plan_key = d.replace("stars_", "")
    plan = VIP_STARS.get(plan_key)
    if not plan:
        return

    await context.bot.send_invoice(
        chat_id=uid,
        title=f"💎 VIP — {plan['label']}",
        description=f"MediaBot VIP obunasi {plan['label']}ga. Barcha VIP kontentlarga kirish!",
        payload=f"vip_{plan_key}",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=f"VIP {plan['label']}", amount=plan["stars"])],
    )

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lovni tasdiqlash"""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def stars_payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov muvaffaqiyatli bo'lganda VIP berish"""
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    payload = update.message.successful_payment.invoice_payload

    # payload: vip_1_oy, vip_3_oy, vip_12_oy
    plan_key = payload.replace("vip_", "")
    plan = VIP_STARS.get(plan_key)

    if plan:
        until = set_vip(uid, plan["days"])
        await update.message.reply_text(
            f"🎉 *To'lov qabul qilindi!*\n\n"
            f"💎 VIP faollashdi!\n"
            f"📅 Muddat: *{plan['label']}*\n"
            f"🗓 Tugash sanasi: *{until}*\n\n"
            f"Barcha VIP kontentlarga kirish ochiq! 🎬",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu")
            ]]),
            parse_mode="Markdown"
        )

        # Adminga xabar
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"💎 *Yangi VIP!*\n\n"
                         f"👤 Foydalanuvchi: {uid}\n"
                         f"📦 Tarif: {plan['label']}\n"
                         f"⭐ Stars: {plan['stars']}\n"
                         f"🗓 Muddat: {until}",
                    parse_mode="Markdown"
                )
            except:
                pass

# =====================
# JOIN REQUEST — AVTOMATIK QABUL
# =====================

async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Foydalanuvchi kanalga arizа yuborsa — avtomatik qabul qiladi.
    Faqat sub_type='invite' bo'lgan kanallar uchun ishlaydi.
    """
    request: ChatJoinRequest = update.chat_join_request
    user = request.from_user
    chat_id = str(request.chat.id)

    # Shu kanal invite rejimida ekanini tekshiramiz
    subs = get_subscriptions()
    is_invite_channel = any(
        str(s["channel_id"]) == chat_id and s["sub_type"] == "invite"
        for s in subs
    )

    if is_invite_channel:
        try:
            await context.bot.approve_chat_join_request(
                chat_id=request.chat.id,
                user_id=user.id
            )
            # Foydalanuvchiga xabar yuboramiz
            lang = get_user_lang(user.id)
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"✅ *{request.chat.title}* kanaliga qabul qilindingiz!\n\n"
                         f"Endi botga qaytishingiz mumkin 👇",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🤖 Botga qaytish", callback_data="check_sub")
                    ]]),
                    parse_mode="Markdown"
                )
            except:
                pass
        except Exception as e:
            logging.error(f"Join request xatosi: {e}")

# =====================
# INLINE QIDIRUV
# =====================

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        return
    from database import search_movies
    from telegram import InlineQueryResultArticle, InputTextMessageContent
    import uuid

    results_db = search_movies(query)
    results = []
    for m in results_db[:10]:
        vip_badge = "💎 " if m["is_vip"] else ""
        results.append(InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"{vip_badge}{m['title']}",
            description=f"📅 {m['year'] or '—'} | ⭐ {m['rating']} | {m['category']}",
            input_message_content=InputTextMessageContent(
                f"/movie_{m['id']}"
            )
        ))
    await update.inline_query.answer(results, cache_time=10)

# =====================
# MAIN
# =====================

def main():
    print("🤖 MediaBot ishga tushmoqda...")
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(InlineQueryHandler(inline_query))

    # Join request — avtomatik qabul qilish
    app.add_handler(ChatJoinRequestHandler(join_request_handler))

    # Telegram Stars to'lov
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, stars_payment_success))

    # Foydalanuvchi xabarlari
    from user import message_handler as user_msg
    from admin import message_handler as admin_msg
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_msg))
    app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO | filters.Document.ALL, admin_msg))

    print("✅ Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
