from datetime import datetime, timezone, timedelta

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from config import (
    ADMIN_ID,
    WEEX_REFERRAL_LINK,
    GROUP_INVITE_LINK,
    GROUP_ID,
    TRIAL_DAYS,
    VERIFY_RATE_LIMIT,
)
from models import User
from weex_api import check_uid_in_referrals

router = Router()


# ---------------------------------------------------------------------------
# FSM state for UID input
# ---------------------------------------------------------------------------
class VerifyState(StatesGroup):
    awaiting_uid = State()


# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------
def kb_welcome():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Start Free Trial", callback_data="start_trial")],
        [InlineKeyboardButton(text="How It Works", callback_data="how_it_works")],
    ])


def kb_how_it_works():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Start Free Trial", callback_data="start_trial")],
        [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
    ])


def kb_trial_started():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Join Private Group", url=GROUP_INVITE_LINK)],
        [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
        [InlineKeyboardButton(text="Verify My UID", callback_data="verify_uid")],
    ])


def kb_post_join():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
        [InlineKeyboardButton(text="Verify My UID", callback_data="verify_uid")],
    ])


def kb_verify_success():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open Group", url=GROUP_INVITE_LINK)],
        [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
    ])


def kb_verify_fail():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
        [InlineKeyboardButton(text="Try Again", callback_data="verify_uid")],
    ])


def kb_verify_prompt():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
        [InlineKeyboardButton(text="Verify My UID", callback_data="verify_uid")],
    ])


def kb_rejoin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Rejoin Private Group", url=GROUP_INVITE_LINK)],
        [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
    ])


def kb_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Cancel", callback_data="cancel_verify")],
    ])


# ---------------------------------------------------------------------------
# Text constants
# ---------------------------------------------------------------------------
WELCOME_TEXT = (
    "Welcome to Shah's Trading Signals.\n\n"
    f"You're eligible for a free {TRIAL_DAYS}-day trial "
    "of our private signals group.\n\n"
    "To keep access after the trial period, simply "
    "create a WEEX account through our link and verify your UID."
)

HOW_IT_WORKS_TEXT = (
    "How It Works\n"
    "-----\n"
    "1. Start your free trial below\n"
    "2. Join the private signals group\n"
    f"3. Enjoy full access for {TRIAL_DAYS} days\n"
    "4. Create a WEEX account using our referral link\n"
    "5. Come back here and verify your UID\n"
    "6. Keep permanent access to the group"
)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
@router.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    # Admin panel
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Admin panel active.\n\n"
            "Commands:\n"
            "/stats  - group statistics\n"
            "/status <user_id>  - check user\n"
            "/reset <user_id>  - reset trial\n"
            "/kick <user_id>  - manual kick\n"
            "/users  - list trial users\n"
            "/users verified  - list verified users\n"
            "/unflag <user_id|all>  - unflag users"
        )
        return

    user = await User.filter(telegram_id=message.from_user.id).first()

    # Brand-new user — welcome screen
    if not user:
        await message.answer(WELCOME_TEXT, reply_markup=kb_welcome())
        return

    # Update profile info (atomic — never overwrite status)
    await User.filter(telegram_id=message.from_user.id).update(
        bot_started=True,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if user.status == "verified":
        await message.answer(
            "Your account is verified.\n\n"
            "You have permanent access to the signals group.",
            reply_markup=kb_verify_success(),
        )
    elif user.status == "trial":
        trial_end = user.join_time + timedelta(days=TRIAL_DAYS)
        remaining = trial_end - datetime.now(timezone.utc)

        # Trial already expired but scheduler hasn't processed yet
        if remaining.total_seconds() <= 0:
            await message.answer(
                "Your trial period has ended.\n\n"
                "You can still verify your WEEX account to keep access.",
                reply_markup=kb_verify_prompt(),
            )
        else:
            days_left = max(0, remaining.days)
            hours_left = max(0, int(remaining.total_seconds() // 3600))
            time_text = f"{days_left} day(s)" if days_left > 0 else f"{hours_left} hour(s)"

            await message.answer(
                f"Your trial is active — {time_text} remaining.\n\n"
                "To keep access after the trial:\n"
                "1. Open the WEEX link and create your account\n"
                "2. Copy your UID from your WEEX profile\n"
                "3. Tap \"Verify My UID\" below",
                reply_markup=kb_post_join(),
            )
    elif user.status in ("kicked", "inactive_kicked"):
        await message.answer(
            "Your trial period has ended and you were removed "
            "from the group.\n\n"
            "You can still verify your WEEX account to regain access.",
            reply_markup=kb_verify_prompt(),
        )
    else:
        await message.answer(WELCOME_TEXT, reply_markup=kb_welcome())


# ---------------------------------------------------------------------------
# Callback: Start Free Trial
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "start_trial")
async def cb_start_trial(callback: CallbackQuery):
    user = await User.filter(telegram_id=callback.from_user.id).first()

    # Already verified
    if user and user.status == "verified":
        await callback.message.edit_text(
            "Your account is already verified.\n\n"
            "You have permanent access to the signals group.",
            reply_markup=kb_verify_success(),
        )
        await callback.answer()
        return

    # Trial already active (or expired but not yet processed)
    if user and user.status == "trial":
        trial_end = user.join_time + timedelta(days=TRIAL_DAYS)
        remaining = trial_end - datetime.now(timezone.utc)

        if remaining.total_seconds() <= 0:
            await callback.message.edit_text(
                "Your trial period has ended.\n\n"
                "To regain access, create a WEEX account through "
                "our link and verify your UID below.",
                reply_markup=kb_verify_prompt(),
            )
            await callback.answer()
            return

        days_left = max(0, remaining.days)
        await callback.message.edit_text(
            f"Your trial is already active — {days_left} day(s) remaining.\n\n"
            "Join the group below, or verify your WEEX account "
            "to secure permanent access.",
            reply_markup=kb_trial_started(),
        )
        await callback.answer()
        return

    # Kicked — cannot restart trial, must verify
    if user and user.status in ("kicked", "inactive_kicked"):
        await callback.message.edit_text(
            "Your trial period has ended.\n\n"
            "To regain access, create a WEEX account through "
            "our link and verify your UID below.",
            reply_markup=kb_verify_prompt(),
        )
        await callback.answer()
        return

    # Create new trial
    now = datetime.now(timezone.utc)

    if user:
        # Edge case: user in unexpected status — reset to trial
        user.status = "trial"
        user.join_time = now
        user.weex_uid = None
        user.verified_time = None
        user.verify_attempts = 0
        user.last_verify_attempt = None
        user.last_reminder = 0
        user.bot_started = True
        user.username = callback.from_user.username
        user.first_name = callback.from_user.first_name
        await user.save()
    else:
        await User.create(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            join_time=now,
            status="trial",
            bot_started=True,
            last_reminder=0,
        )

    trial_end = now + timedelta(days=TRIAL_DAYS)

    await callback.message.edit_text(
        f"Your {TRIAL_DAYS}-day free trial has started.\n\n"
        f"Access expires on {trial_end.strftime('%b %d, %Y at %H:%M UTC')}.\n\n"
        "Join the private signals group below.\n"
        "Before your trial ends, verify your WEEX account "
        "to keep permanent access.",
        reply_markup=kb_trial_started(),
    )
    await callback.answer()
    logger.info(f"Trial started for {callback.from_user.id} (@{callback.from_user.username})")


# ---------------------------------------------------------------------------
# Callback: How It Works
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "how_it_works")
async def cb_how_it_works(callback: CallbackQuery):
    await callback.message.edit_text(
        HOW_IT_WORKS_TEXT,
        reply_markup=kb_how_it_works(),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Callback: Verify My UID — ask user to paste UID
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "verify_uid")
async def cb_verify_uid(callback: CallbackQuery, state: FSMContext):
    user = await User.filter(telegram_id=callback.from_user.id).first()

    if user and user.status == "verified":
        await callback.message.edit_text(
            "Your account is already verified.\n\n"
            "You have permanent access to the signals group.",
            reply_markup=kb_verify_success(),
        )
        await callback.answer()
        return

    # Rate limit check
    if user and user.last_verify_attempt:
        now = datetime.now(timezone.utc)
        elapsed = (now - user.last_verify_attempt).total_seconds()
        if elapsed < 3600 and user.verify_attempts >= VERIFY_RATE_LIMIT:
            wait_min = int((3600 - elapsed) / 60)
            await callback.answer(
                f"Too many attempts. Try again in ~{wait_min} min.",
                show_alert=True,
            )
            return

    await state.set_state(VerifyState.awaiting_uid)
    await callback.message.edit_text(
        "Enter your WEEX UID below.\n\n"
        "Your UID is a number found in your WEEX profile settings.\n"
        "Example: 123456789",
        reply_markup=kb_cancel(),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Callback: Cancel verify
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "cancel_verify")
async def cb_cancel_verify(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await User.filter(telegram_id=callback.from_user.id).first()

    if user and user.status == "trial":
        await callback.message.edit_text(
            "Verification cancelled.\n\n"
            "You can verify anytime before your trial expires.",
            reply_markup=kb_post_join(),
        )
    elif user and user.status in ("kicked", "inactive_kicked"):
        await callback.message.edit_text(
            "Verification cancelled.\n\n"
            "Verify your WEEX account when you're ready to rejoin.",
            reply_markup=kb_verify_prompt(),
        )
    else:
        await callback.message.edit_text(WELCOME_TEXT, reply_markup=kb_welcome())
    await callback.answer()


# ---------------------------------------------------------------------------
# Message: UID input (FSM state)
# ---------------------------------------------------------------------------
@router.message(StateFilter(VerifyState.awaiting_uid), F.chat.type == "private")
async def process_uid_input(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    user = await User.filter(telegram_id=message.from_user.id).first()

    if not user:
        await message.answer(WELCOME_TEXT, reply_markup=kb_welcome())
        return

    if user.status == "verified":
        await message.answer(
            "You're already verified!",
            reply_markup=kb_verify_success(),
        )
        return

    weex_uid = message.text.strip() if message.text else ""

    # Validate: numbers only
    if not weex_uid.isdigit():
        await message.answer(
            "Please enter numbers only.\n\nExample: 123456789",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Try Again", callback_data="verify_uid")],
                [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
            ]),
        )
        return

    # Check duplicate UID
    existing = await User.filter(weex_uid=weex_uid).first()
    if existing and existing.telegram_id != user.telegram_id:
        await message.answer(
            "This WEEX UID is already linked to another account.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Try Again", callback_data="verify_uid")],
                [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
            ]),
        )
        return

    # Rate limit
    now = datetime.now(timezone.utc)
    if user.last_verify_attempt:
        elapsed = (now - user.last_verify_attempt).total_seconds()
        if elapsed < 3600 and user.verify_attempts >= VERIFY_RATE_LIMIT:
            wait_min = int((3600 - elapsed) / 60)
            await message.answer(f"Too many attempts. Try again in ~{wait_min} min.")
            return
        if elapsed >= 3600:
            user.verify_attempts = 0

    user.verify_attempts += 1
    user.last_verify_attempt = now
    await User.filter(id=user.id).update(
        verify_attempts=user.verify_attempts,
        last_verify_attempt=now,
    )

    verifying_msg = await message.answer("Verifying your WEEX UID...")

    is_valid = await check_uid_in_referrals(weex_uid)

    # API error — don't punish user
    if is_valid is None:
        await verifying_msg.edit_text(
            "Verification temporarily unavailable. Please try again in a few minutes.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Try Again", callback_data="verify_uid")],
            ]),
        )
        return

    if is_valid:
        was_kicked = user.status in ("kicked", "inactive_kicked")

        user.status = "verified"
        user.weex_uid = weex_uid
        user.verified_time = now
        await User.filter(id=user.id).update(
            status="verified",
            weex_uid=weex_uid,
            verified_time=now,
        )

        logger.info(f"User {user.telegram_id} verified with WEEX UID {weex_uid}")

        if was_kicked:
            # Unban so they can rejoin
            try:
                await bot.unban_chat_member(GROUP_ID, user.telegram_id, only_if_banned=True)
                logger.info(f"Unbanned verified user {user.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to unban user {user.telegram_id}: {e}")

            await verifying_msg.edit_text(
                "Verification successful.\n\n"
                "Your account is confirmed. "
                "Tap below to rejoin the private signals group.",
                reply_markup=kb_rejoin(),
            )
        else:
            await verifying_msg.edit_text(
                "Verification successful.\n\n"
                "Your account is confirmed. "
                "You now have permanent access to the signals group.",
                reply_markup=kb_verify_success(),
            )
    else:
        await verifying_msg.edit_text(
            "UID not found under our referral.\n\n"
            "Please make sure that:\n"
            "- Your account was created using our referral link\n"
            "- The UID you entered is correct\n\n"
            "If you just registered, please wait a few minutes "
            "and try again.",
            reply_markup=kb_verify_fail(),
        )


# ---------------------------------------------------------------------------
# /verify fallback — redirect to button flow
# ---------------------------------------------------------------------------
@router.message(Command("verify"), F.chat.type == "private")
async def cmd_verify_fallback(message: Message):
    await message.answer(
        "Please use the button below to verify.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Verify My UID", callback_data="verify_uid")],
            [InlineKeyboardButton(text="Open WEEX Link", url=WEEX_REFERRAL_LINK)],
        ]),
    )


@router.message(Command("verify"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_verify_group(message: Message):
    await message.reply("Please send /start to the bot in a private chat.")


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------
@router.message(Command("help"), F.chat.type == "private")
async def cmd_help(message: Message, state: FSMContext):
    await cmd_start(message, state)
