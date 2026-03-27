from datetime import datetime, timezone

from aiogram import Router, Bot
from aiogram.types import ChatJoinRequest, ChatMemberUpdated
from loguru import logger

from config import GROUP_ID, ADMIN_ID
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


@router.chat_join_request()
async def on_join_request(event: ChatJoinRequest, bot: Bot):
    """Auto-approve/decline join requests based on user status."""
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

        # Trial or verified — approve
        await _safe_approve(event)
        await User.filter(telegram_id=tg_user.id).update(
            username=tg_user.username,
            first_name=tg_user.first_name,
        )
        logger.info(f"Approved join request from {tg_user.id} (@{tg_user.username}), status={existing.status}")
        return

    # User not in DB — they skipped the bot. Create a trial record and approve.
    now = datetime.now(timezone.utc)
    await User.create(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        join_time=now,
        status="trial",
        last_reminder=0,
    )
    await _safe_approve(event)
    logger.info(f"Approved join request from new user {tg_user.id} (@{tg_user.username}), created trial")


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, bot: Bot):
    """Fallback: catches direct adds or joins without a join request."""
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

    # User not in DB — create trial record
    now = datetime.now(timezone.utc)
    await User.create(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        join_time=now,
        status="trial",
        last_reminder=0,
    )
    logger.info(f"New user {tg_user.id} joined group directly, created trial")
