from datetime import datetime, timezone

from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger

from config import ADMIN_ID, GROUP_ID, TRIAL_DAYS
from models import User

router = Router()
router.message.filter(F.chat.type == "private", F.from_user.id == ADMIN_ID)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    total = await User.all().count()
    trial = await User.filter(status="trial").count()
    verified = await User.filter(status="verified").count()
    kicked = await User.filter(status="kicked").count()
    flagged = await User.filter(status="flagged").count()
    inactive = await User.filter(status="inactive_kicked").count()

    await message.answer(
        f"Stats:\n"
        f"Total users: {total}\n"
        f"Trial: {trial}\n"
        f"Verified: {verified}\n"
        f"Kicked (trial expired): {kicked}\n"
        f"Kicked (inactive): {inactive}\n"
        f"Flagged: {flagged}"
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /status <telegram_user_id>")
        return

    try:
        target_id = int(args[1].strip())
    except ValueError:
        await message.answer("Invalid user ID.")
        return

    user = await User.filter(telegram_id=target_id).first()
    if not user:
        await message.answer("User not found in database.")
        return

    verified_str = user.verified_time.strftime("%Y-%m-%d %H:%M UTC") if user.verified_time else "N/A"
    await message.answer(
        f"User: @{user.username or 'N/A'} ({user.first_name or 'N/A'})\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Status: {user.status}\n"
        f"Joined: {user.join_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"WEEX UID: {user.weex_uid or 'N/A'}\n"
        f"Verified: {verified_str}\n"
        f"Bot started: {'Yes' if user.bot_started else 'No'}\n"
        f"Verify attempts: {user.verify_attempts}"
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message, bot: Bot):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /reset <telegram_user_id>")
        return

    try:
        target_id = int(args[1].strip())
    except ValueError:
        await message.answer("Invalid user ID.")
        return

    user = await User.filter(telegram_id=target_id).first()
    if not user:
        await message.answer("User not found in database.")
        return

    user.status = "trial"
    user.join_time = datetime.now(timezone.utc)
    user.weex_uid = None
    user.verified_time = None
    user.verify_attempts = 0
    user.last_verify_attempt = None
    await user.save()

    try:
        await bot.unban_chat_member(GROUP_ID, target_id, only_if_banned=True)
    except Exception:
        pass

    await message.answer(
        f"Reset user {target_id}. New {TRIAL_DAYS}-day trial started.\n"
        f"User is unbanned and can rejoin the group."
    )
    logger.info(f"Admin reset trial for user {target_id}")


@router.message(Command("kick"))
async def cmd_kick(message: Message, bot: Bot):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /kick <telegram_user_id>")
        return

    try:
        target_id = int(args[1].strip())
    except ValueError:
        await message.answer("Invalid user ID.")
        return

    user = await User.filter(telegram_id=target_id).first()

    try:
        await bot.ban_chat_member(GROUP_ID, target_id)
        if user:
            user.status = "kicked"
            await user.save()
        await message.answer(f"Kicked and banned user {target_id}.")
        logger.info(f"Admin kicked user {target_id}")
    except Exception as e:
        await message.answer(f"Failed to kick: {e}")


@router.message(Command("users"))
async def cmd_users(message: Message):
    trial_users = await User.filter(status="trial").order_by("join_time").limit(50)
    if not trial_users:
        await message.answer("No users in trial.")
        return

    lines = []
    now = datetime.now(timezone.utc)
    for u in trial_users:
        from datetime import timedelta
        remaining = (u.join_time + timedelta(days=TRIAL_DAYS)) - now
        days_left = max(0, remaining.days)
        lines.append(f"@{u.username or 'N/A'} | ID: {u.telegram_id} | {days_left}d left")

    await message.answer("Trial users:\n\n" + "\n".join(lines))
