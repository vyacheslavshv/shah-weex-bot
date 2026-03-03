from datetime import datetime, timezone, timedelta

from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from loguru import logger

from config import GROUP_ID, ADMIN_ID, WEEX_REFERRAL_LINK, TRIAL_DAYS
from models import User

router = Router()


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, bot: Bot):
    if event.chat.id != GROUP_ID:
        return

    old = event.old_chat_member.status
    new = event.new_chat_member.status
    tg_user = event.new_chat_member.user

    if tg_user.is_bot or tg_user.id == ADMIN_ID:
        return

    is_join = old in ("left", "kicked") and new in ("member", "restricted")
    if not is_join:
        return

    existing = await User.filter(telegram_id=tg_user.id).first()
    if existing:
        if existing.status in ("kicked", "inactive_kicked"):
            try:
                await bot.ban_chat_member(GROUP_ID, tg_user.id)
            except Exception:
                pass
            logger.info(f"Blocked re-join of kicked user {tg_user.id} (@{tg_user.username})")
        elif existing.status == "trial":
            existing.username = tg_user.username
            existing.first_name = tg_user.first_name
            await existing.save()
        return

    now = datetime.now(timezone.utc)
    await User.create(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        join_time=now,
        status="trial",
    )

    trial_end = now + timedelta(days=TRIAL_DAYS)
    text = (
        f"Welcome! You have a {TRIAL_DAYS}-day trial.\n"
        f"Trial ends: {trial_end.strftime('%b %d, %Y %H:%M UTC')}\n\n"
        f"To stay permanently:\n"
        f"1. Register on WEEX: {WEEX_REFERRAL_LINK}\n"
        f"2. Get your WEEX UID from your profile\n"
        f"3. DM me and press /start, then send /verify YOUR_WEEX_UID"
    )
    try:
        await bot.send_message(tg_user.id, text)
        logger.info(f"Sent welcome DM to {tg_user.id} (@{tg_user.username})")
    except Exception:
        try:
            await bot.send_message(
                GROUP_ID,
                f"{tg_user.mention_html()}, welcome! You have {TRIAL_DAYS} days to verify.\n"
                f"Please DM me and press /start to get instructions.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Could not notify new user {tg_user.id}: {e}")
