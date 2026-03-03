from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
from loguru import logger

from config import GROUP_ID, ADMIN_ID, TRIAL_DAYS, INACTIVITY_DAYS, INACTIVITY_ACTION
from models import User
from weex_api import has_recent_activity

scheduler = AsyncIOScheduler()


async def check_trial_expiry(bot: Bot):
    cutoff = datetime.now(timezone.utc) - timedelta(days=TRIAL_DAYS)
    expired = await User.filter(status="trial", join_time__lt=cutoff).all()

    for user in expired:
        try:
            await bot.ban_chat_member(GROUP_ID, user.telegram_id)
            user.status = "kicked"
            await user.save()
            logger.info(f"Kicked expired trial: {user.telegram_id} (@{user.username})")

            if user.bot_started:
                try:
                    await bot.send_message(
                        user.telegram_id,
                        "Your trial period has expired and you've been removed from the group.\n"
                        "Contact the admin if you believe this is an error."
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to kick expired user {user.telegram_id}: {e}")


async def check_inactivity(bot: Bot):
    verified = await User.filter(status="verified", weex_uid__not_isnull=True).all()

    for user in verified:
        if not user.weex_uid:
            continue

        active = await has_recent_activity(user.weex_uid, INACTIVITY_DAYS)
        if active is None:
            logger.warning(f"Could not check activity for {user.telegram_id} (UID: {user.weex_uid})")
            continue

        user.last_trade_check = datetime.now(timezone.utc)

        if not active:
            if INACTIVITY_ACTION == "ban":
                try:
                    await bot.ban_chat_member(GROUP_ID, user.telegram_id)
                    user.status = "inactive_kicked"
                    await user.save()
                    logger.info(f"Kicked inactive user {user.telegram_id}")
                except Exception as e:
                    logger.error(f"Failed to kick inactive user {user.telegram_id}: {e}")
                    continue
            else:
                user.status = "flagged"
                await user.save()
                logger.info(f"Flagged inactive user {user.telegram_id}")
                try:
                    await bot.send_message(
                        ADMIN_ID,
                        f"Inactive user flagged:\n"
                        f"@{user.username or 'N/A'} (ID: {user.telegram_id})\n"
                        f"WEEX UID: {user.weex_uid}\n"
                        f"No trading activity for {INACTIVITY_DAYS}+ days"
                    )
                except Exception:
                    pass
        else:
            await user.save()


def start_scheduler(bot: Bot):
    scheduler.add_job(
        check_trial_expiry,
        IntervalTrigger(hours=1),
        args=[bot],
        id="trial_expiry",
        replace_existing=True,
    )
    scheduler.add_job(
        check_inactivity,
        IntervalTrigger(hours=24),
        args=[bot],
        id="inactivity_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (trial check: hourly, inactivity check: daily)")
