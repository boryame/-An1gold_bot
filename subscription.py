from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from database import get_subscriptions

async def check_subscription(user_id: int, context) -> list:
    """
    Foydalanuvchi barcha kanallarga obuna bo'lganini tekshiradi.
    Obuna bo'lmagan kanallar ro'yxatini qaytaradi.
    Bo'sh ro'yxat = hammasi OK.
    """
    channels = get_subscriptions()
    not_subbed = []

    for ch in channels:
        try:
            ch_id = ch["channel_id"]
            sub_type = ch["sub_type"]
            min_members = ch["min_members"] or 0

            # === MIN MEMBERS TEKSHIRISH ===
            if min_members > 0:
                try:
                    count = await context.bot.get_chat_member_count(ch_id)
                    if count < min_members:
                        # Kanal hali yetarli obunachiga ega emas — o'tkazamiz
                        continue
                except:
                    pass

            # === ZAYAVKA (INVITE) ===
            if sub_type == "invite":
                try:
                    member = await context.bot.get_chat_member(
                        chat_id=ch_id,
                        user_id=user_id
                    )
                    if member.status in ("member", "administrator", "creator"):
                        continue
                    else:
                        not_subbed.append(dict(ch))
                except TelegramError:
                    # Maxfiy kanal — tekshirib bo'lmasa o'tkazamiz
                    continue

            # === OMMAVIY VA MAXFIY ===
            else:
                member = await context.bot.get_chat_member(
                    chat_id=ch_id,
                    user_id=user_id
                )
                if member.status in ("member", "administrator", "creator"):
                    continue
                elif member.status in ("left", "kicked"):
                    not_subbed.append(dict(ch))

        except TelegramError:
            # Kanal topilmasa yoki bot admin emas — o'tkazib yuboramiz
            pass

    return not_subbed
