"""Pyrogram client factory and handler registration."""

from __future__ import annotations

import logging

from pyrogram import Client

from app.config import API_HASH, API_ID, BOT_TOKEN, SESSION_NAME
from app.handlers import register_handlers

logger = logging.getLogger(__name__)


def create_bot() -> Client:
    """Build the Pyrogram client and attach all handlers."""
    bot = Client(
        SESSION_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,
    )
    register_handlers(bot)
    logger.info("Bot handlers registered.")
    return bot
