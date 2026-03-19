from datetime import datetime, timezone, timedelta

from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger

from config import ADMIN_ID, GROUP_ID, TRIAL_DAYS
from models import User

router = Router()
router.message.filter(F.chat.type == "private", F.from_user.id == ADMIN_ID)

USERS_PAGE_SIZE = 30


@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot):
    total = await User.all().count()
    trial = await User.filter(status="trial").count()
    verified = await User.filter(status="verified").count()
    kicked = await User.filter(status="kicked").count()
    inactive_kicked = await User.filter(status="inactive_kicked").count()
    flagged = await User.filter(status="flagged").count()

    # Try to get live group member count
    group_members = "N/A"
    try:
        count = await bot.get_chat_member_count(GROUP_ID)
        group_members = str(count)
    except Exception:
        pass

    await message.answer(
        f"Stats:\n\n"
        f"Total DB users: {total}\n"
        f"Live group members: {group_members}\n\n"
        f"Trial: {trial}\n"
        f"Verified: {verified}\n"
        f"Removed (trial expired): {kicked}\n"
        f"Removed (inactive): {inactive_kicked}\n"
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
    trial_end = user.join_time + timedelta(days=TRIAL_DAYS)
    remaining = trial_end - datetime.now(timezone.utc)
    days_left = max(0, remaining.days)

    await message.answer(
        f"User: @{user.username or 'N/A'} ({user.first_name or 'N/A'})\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Status: {user.status}\n"
        f"Joined: {user.join_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"Trial ends: {trial_end.strftime('%Y-%m-%d %H:%M UTC')} ({days_left}d left)\n"
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
    user.last_reminder = 0
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
    args = message.text.split(maxsplit=2)
    # /users verified [page]
    if len(args) >= 2 and args[1].strip().lower() == "verified":
        page = 1
        if len(args) >= 3:
            try:
                page = max(1, int(args[2].strip()))
            except ValueError:
                pass
        await _list_users(message, "verified", page)
        return

    # /users [page] — defaults to trial
    page = 1
    if len(args) >= 2:
        try:
            page = max(1, int(args[1].strip()))
        except ValueError:
            pass
    await _list_users(message, "trial", page)


async def _list_users(message: Message, status: str, page: int):
    total = await User.filter(status=status).count()
    if total == 0:
        await message.answer(f"No {status} users.")
        return

    total_pages = max(1, (total + USERS_PAGE_SIZE - 1) // USERS_PAGE_SIZE)
    page = min(page, total_pages)
    offset = (page - 1) * USERS_PAGE_SIZE

    users = await User.filter(status=status).order_by("join_time").offset(offset).limit(USERS_PAGE_SIZE)

    lines = []
    now = datetime.now(timezone.utc)
    for u in users:
        if status == "trial":
            remaining = (u.join_time + timedelta(days=TRIAL_DAYS)) - now
            days_left = max(0, remaining.days)
            lines.append(f"@{u.username or 'N/A'} | ID: {u.telegram_id} | {days_left}d left")
        else:
            uid_str = u.weex_uid or "N/A"
            lines.append(f"@{u.username or 'N/A'} | ID: {u.telegram_id} | UID: {uid_str}")

    header = f"{status.capitalize()} users ({total} total) — page {page}/{total_pages}:\n\n"
    await message.answer(header + "\n".join(lines))


@router.message(Command("unflag"))
async def cmd_unflag(message: Message):
    args = message.text.split(maxsplit=1)

    if len(args) >= 2 and args[1].strip().lower() == "all":
        count = await User.filter(status="flagged").update(status="verified")
        await message.answer(f"Unflagged {count} user(s). Status set back to verified.")
        logger.info(f"Admin unflagged all ({count} users)")
        return

    if len(args) < 2:
        await message.answer("Usage:\n/unflag <telegram_user_id>\n/unflag all")
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

    if user.status != "flagged":
        await message.answer(f"User is not flagged (current status: {user.status}).")
        return

    user.status = "verified"
    await user.save()
    await message.answer(f"User {target_id} unflagged. Status: verified.")
    logger.info(f"Admin unflagged user {target_id}")
