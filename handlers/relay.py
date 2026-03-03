from aiogram import Router, Bot, F
from aiogram.types import Message
from loguru import logger

from config import ADMIN_ID
from models import RelayMessage

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def admin_reply(message: Message, bot: Bot):
    """Admin replies to a forwarded message -> deliver to user."""
    relay = await RelayMessage.filter(
        forwarded_msg_id=message.reply_to_message.message_id
    ).first()
    if not relay:
        return

    try:
        await bot.copy_message(
            chat_id=relay.user_telegram_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except Exception as e:
        await message.answer(f"Could not deliver message: {e}")
        logger.error(f"Relay delivery failed to {relay.user_telegram_id}: {e}")


@router.message(F.from_user.id != ADMIN_ID)
async def user_dm(message: Message, bot: Bot):
    """User sends DM -> forward to admin."""
    try:
        forwarded = await message.forward(ADMIN_ID)
        await RelayMessage.create(
            forwarded_msg_id=forwarded.message_id,
            user_telegram_id=message.from_user.id,
        )
    except Exception as e:
        logger.error(f"Relay forward failed from {message.from_user.id}: {e}")
