from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from config import GROUP_ID, ADMIN_ID, TRIAL_DAYS, WEEX_REFERRAL_LINK, GROUP_INVITE_LINK
from models import User

scheduler = AsyncIOScheduler()


# ---------------------------------------------------------------------------
# Keyboards used in scheduler messages
# ---------------------------------------------------------------------------
def _kb_verify_prompt():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
        [InlineKeyboardButton(text="Verify My UID", callback_data="verify_uid")],
    ])


# ---------------------------------------------------------------------------
# Reminder messages
# ---------------------------------------------------------------------------
REMINDER_MESSAGES = {
    1: (
        "Your free trial is now active.\n\n"
        "To keep access after the trial period, create a WEEX account "
        "through our referral link and verify your UID."
    ),
    2: (
        "Trial reminder — Day 2\n\n"
        "Have you created your WEEX account yet? "
        "Verify your UID to secure permanent access to the group."
    ),
    3: (
        "Trial reminder — 2 days remaining\n\n"
        "Your trial is ending soon. Verify your WEEX account now "
        "to avoid losing access to the signals group."
    ),
    4: (
        "Trial reminder — Less than 24 hours left\n\n"
        "Your access expires tomorrow. "
        "Verify your WEEX UID now to keep your spot in the group."
    ),
    5: (
        "Final reminder — About 2 hours left\n\n"
        "Your trial is about to expire. "
        "This is your last chance to verify and keep access."
    ),
}


# ---------------------------------------------------------------------------
# Trial expiry: kick unverified users after trial ends
# ---------------------------------------------------------------------------
async def check_trial_expiry(bot: Bot):
    cutoff = datetime.now(timezone.utc) - timedelta(days=TRIAL_DAYS)
    expired = await User.filter(status="trial", bot_started=True, join_time__lt=cutoff).all()

    for user in expired:
        # Atomic update: only proceed if status is still "trial"
        updated = await User.filter(id=user.id, status="trial").update(status="kicked")
        if not updated:
            # Already processed by a previous run or concurrent job — skip
            continue

        try:
            await bot.ban_chat_member(GROUP_ID, user.telegram_id)
            logger.info(f"Kicked expired trial: {user.telegram_id} (@{user.username})")
        except Exception as e:
            logger.warning(f"Could not kick {user.telegram_id} from group (may not be member): {e}")

        if user.bot_started:
            try:
                await bot.send_message(
                    user.telegram_id,
                    "Your trial period has ended and you have been "
                    "removed from the group.\n\n"
                    "You can still verify your WEEX account to regain access.",
                    reply_markup=_kb_verify_prompt(),
                )
            except Exception:
                pass

        try:
            await bot.send_message(
                ADMIN_ID,
                f"Removed expired trial user:\n"
                f"@{user.username or 'N/A'} (ID: {user.telegram_id})",
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Reminders: send at specific points during trial
#   1 = 1 hour after start
#   2 = day 2
#   3 = day 5
#   4 = 24 hours before expiry
#   5 = 2 hours before expiry
# ---------------------------------------------------------------------------
async def send_reminders(bot: Bot):
    now = datetime.now(timezone.utc)
    # Only get users whose trial has NOT yet expired
    cutoff = now - timedelta(days=TRIAL_DAYS)
    trial_users = await User.filter(
        status="trial", bot_started=True, join_time__gt=cutoff
    ).all()

    for user in trial_users:
        trial_end = user.join_time + timedelta(days=TRIAL_DAYS)
        elapsed = now - user.join_time
        remaining = trial_end - now

        elapsed_hours = elapsed.total_seconds() / 3600
        remaining_hours = remaining.total_seconds() / 3600

        last = user.last_reminder or 0

        # Determine which reminder to send next
        next_reminder = None
        if last < 1 and elapsed_hours >= 1:
            next_reminder = 1
        elif last < 2 and elapsed.days >= 2:
            next_reminder = 2
        elif last < 3 and elapsed.days >= 5:
            next_reminder = 3
        elif last < 4 and remaining_hours <= 24:
            next_reminder = 4
        elif last < 5 and remaining_hours <= 2:
            next_reminder = 5

        if next_reminder and next_reminder in REMINDER_MESSAGES:
            try:
                await bot.send_message(
                    user.telegram_id,
                    REMINDER_MESSAGES[next_reminder],
                    reply_markup=_kb_verify_prompt(),
                )
                # Atomic update — only touch last_reminder, never overwrite status
                await User.filter(id=user.id).update(last_reminder=next_reminder)
                logger.info(f"Sent reminder #{next_reminder} to {user.telegram_id}")
            except Exception as e:
                logger.warning(f"Failed to send reminder to {user.telegram_id}: {e}")


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------
def start_scheduler(bot: Bot):
    scheduler.add_job(
        check_trial_expiry,
        IntervalTrigger(hours=1),
        args=[bot],
        id="trial_expiry",
        replace_existing=True,
    )
    scheduler.add_job(
        send_reminders,
        IntervalTrigger(hours=1),
        args=[bot],
        id="reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (trial expiry: hourly, reminders: hourly)")
