"""Force-join channel membership check and its keyboard."""

from __future__ import annotations

import logging

from pyrogram import Client, enums
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import CHANNEL_URL, CHANNEL_USERNAME

logger = logging.getLogger(__name__)

_ALLOWED_STATUSES = {
    enums.ChatMemberStatus.OWNER,
    enums.ChatMemberStatus.ADMINISTRATOR,
    enums.ChatMemberStatus.MEMBER,
}


async def check_user_joined(client: Client, user_id: int) -> bool:
    """Return True if the user is a member of the required channel.

    On unexpected (non-membership) errors we fail open -- the user is allowed
    through rather than being locked out by a transient Telegram API issue.
    """
    try:
        member = await client.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in _ALLOWED_STATUSES
    except UserNotParticipant:
        return False
    except Exception:  # noqa: BLE001 - deliberate fail-open on unknown errors
        logger.exception("Error checking channel membership for user_id=%s", user_id)
        return True


def get_force_join_markup() -> InlineKeyboardMarkup:
    """Build the Join Channel / Check Join inline keyboard."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("Check Join 🟢", callback_data="check_join")],
        ]
    )
