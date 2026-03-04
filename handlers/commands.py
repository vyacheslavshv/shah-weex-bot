from datetime import datetime, timezone, timedelta

from aiogram import Router, F
from aiogram.types import Message, LinkPreviewOptions
from aiogram.filters import Command
from loguru import logger

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

from config import ADMIN_ID, WEEX_REFERRAL_LINK, TRIAL_DAYS, VERIFY_RATE_LIMIT
from models import User
from weex_api import check_uid_in_referrals

router = Router()


@router.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Admin panel active.\n\n"
            "Commands:\n"
            "/stats — group statistics\n"
            "/status <user_id> — check user\n"
            "/reset <user_id> — reset trial\n"
            "/kick <user_id> — manual kick\n"
            "/users — list trial users"
        )
        return

    user = await User.filter(telegram_id=message.from_user.id).first()
    if not user:
        await message.answer(
            "Welcome! Join the group first, then use /verify to verify your WEEX account."
        )
        return

    user.bot_started = True
    await user.save()

    if user.status == "verified":
        await message.answer("You're verified! No action needed.")
    elif user.status == "trial":
        trial_end = user.join_time + timedelta(days=TRIAL_DAYS)
        remaining = trial_end - datetime.now(timezone.utc)
        days_left = max(0, remaining.days)
        await message.answer(
            f"Your trial has {days_left} day(s) remaining.\n\n"
            f"To verify, register on WEEX:\n{WEEX_REFERRAL_LINK}\n\n"
            f"Then send: /verify YOUR_WEEX_UID",
            link_preview_options=NO_PREVIEW,
        )
    else:
        await message.answer(
            "Your trial has expired. Contact the admin for assistance."
        )


@router.message(Command("verify"), F.chat.type == "private")
async def cmd_verify(message: Message):
    user = await User.filter(telegram_id=message.from_user.id).first()
    if not user:
        await message.answer("You need to join the group first.")
        return

    if user.status == "verified":
        await message.answer("You're already verified!")
        return

    now = datetime.now(timezone.utc)
    if user.last_verify_attempt:
        elapsed = (now - user.last_verify_attempt).total_seconds()
        if elapsed < 3600 and user.verify_attempts >= VERIFY_RATE_LIMIT:
            wait_min = int((3600 - elapsed) / 60)
            await message.answer(f"Too many attempts. Try again in ~{wait_min} min.")
            return
        if elapsed >= 3600:
            user.verify_attempts = 0

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /verify YOUR_WEEX_UID\nExample: /verify 123456789")
        return

    weex_uid = args[1].strip()

    existing = await User.filter(weex_uid=weex_uid).first()
    if existing and existing.telegram_id != user.telegram_id:
        await message.answer("This WEEX UID is already linked to another account.")
        return

    user.verify_attempts += 1
    user.last_verify_attempt = now
    await user.save()

    await message.answer("Verifying your WEEX UID...")

    is_valid = await check_uid_in_referrals(weex_uid)

    if is_valid:
        user.status = "verified"
        user.weex_uid = weex_uid
        user.verified_time = now
        await user.save()
        await message.answer("Verified! You now have permanent access to the group.")
        logger.info(f"User {user.telegram_id} verified with WEEX UID {weex_uid}")
    else:
        await message.answer(
            "UID not found under our referral.\n\n"
            f"Make sure you registered using this link:\n{WEEX_REFERRAL_LINK}\n\n"
            "If you just registered, wait a few minutes and try again.",
            link_preview_options=NO_PREVIEW,
        )


@router.message(Command("verify"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_verify_group(message: Message):
    await message.reply("Please send /verify in my DMs (private chat).")


@router.message(Command("help"), F.chat.type == "private")
async def cmd_help(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Admin commands:\n"
            "/stats — group statistics\n"
            "/status <user_id> — check user info\n"
            "/reset <user_id> — reset trial\n"
            "/kick <user_id> — manual kick\n"
            "/users — list trial users\n\n"
            "Chat relay: reply to any forwarded message to respond to a user."
        )
    else:
        await message.answer(
            "Commands:\n"
            "/start — show your status\n"
            "/verify <weex_uid> — verify your WEEX account\n"
            "/help — this message"
        )
