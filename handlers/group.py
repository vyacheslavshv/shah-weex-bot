from datetime import datetime, timezone, timedelta

from aiogram import Router, Bot
from aiogram.types import ChatJoinRequest, ChatMemberUpdated
from loguru import logger

from config import GROUP_ID, ADMIN_ID, WEEX_REFERRAL_LINK, TRIAL_DAYS
from models import User

router = Router()


async def _safe_approve(event: ChatJoinRequest):
    try:
        await event.approve()
    except Exception:
        pass


async def _safe_decline(event: ChatJoinRequest):
    try:
        await event.decline()
    except Exception:
        pass


def _welcome_text(trial_end):
    return (
        f"Welcome! You've been approved to join the group.\n\n"
        f"You have a {TRIAL_DAYS}-day trial period.\n"
        f"Trial ends: {trial_end.strftime('%b %d, %Y %H:%M UTC')}\n\n"
        f"To stay permanently:\n"
        f"1. Register on WEEX: {WEEX_REFERRAL_LINK}\n"
        f"2. Find your WEEX UID in your profile settings\n"
        f"3. Come back here, press /start, then send /verify YOUR_UID\n\n"
        f"Press /start to activate the bot — without it I won't be able "
        f"to send you reminders or updates."
    )


@router.chat_join_request()
async def on_join_request(event: ChatJoinRequest, bot: Bot):
    """Primary flow: group has invite link with admin approval required."""
    if event.chat.id != GROUP_ID:
        return

    tg_user = event.from_user

    if tg_user.is_bot or tg_user.id == ADMIN_ID:
        await _safe_approve(event)
        return

    existing = await User.filter(telegram_id=tg_user.id).first()
    if existing:
        if existing.status in ("kicked", "inactive_kicked"):
            await _safe_decline(event)
            logger.info(f"Declined join request from kicked user {tg_user.id} (@{tg_user.username})")
            return
        await _safe_approve(event)
        if existing.status == "trial":
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

    await _safe_approve(event)

    trial_end = now + timedelta(days=TRIAL_DAYS)
    try:
        await bot.send_message(event.user_chat_id, _welcome_text(trial_end))
        logger.info(f"Sent welcome DM to {tg_user.id} (@{tg_user.username}) via user_chat_id")
    except Exception as e:
        logger.warning(f"Could not DM user {tg_user.id} via user_chat_id: {e}")


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, bot: Bot):
    """Fallback: catches direct adds by admin or joins without a join request."""
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
    try:
        await bot.send_message(tg_user.id, _welcome_text(trial_end))
        logger.info(f"Sent welcome DM to {tg_user.id} (@{tg_user.username})")
    except Exception:
        logger.info(f"New user {tg_user.id} joined without join request, could not DM")
