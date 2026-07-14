"""Telegram update handlers: commands, file uploads, and callback buttons."""

from __future__ import annotations

import logging
import os
import re
import uuid

from pyrogram import Client, enums, filters
from pyrogram.types import CallbackQuery, Message

from app import messages
from app.config import DOWNLOAD_DIR, MAX_FILE_SIZE_MB
from app.dark_config import DarkConfigError, build_unlocked_dark_uri, process_dark_config
from app.force_join import check_user_joined, get_force_join_markup

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def register_handlers(bot: Client) -> None:
    """Attach all message/callback handlers to the given Pyrogram client."""

    @bot.on_message(filters.command("start"))
    async def start_handler(client: Client, message: Message) -> None:
        try:
            if not await check_user_joined(client, message.from_user.id):
                await message.reply_text(
                    messages.FORCE_JOIN_START, reply_markup=get_force_join_markup()
                )
                return
            await message.reply_text(messages.WELCOME, parse_mode=enums.ParseMode.MARKDOWN)
        except Exception:  # noqa: BLE001
            logger.exception("Error in /start handler")

    @bot.on_message(filters.document)
    async def file_handler(client: Client, message: Message) -> None:
        document = message.document
        filename = (document.file_name or "").lower()

        if ".dark" not in filename:
            await message.reply_text(messages.UNSUPPORTED_FILE)
            return

        try:
            if not await check_user_joined(client, message.from_user.id):
                await message.reply_text(
                    messages.FORCE_JOIN_FILE, reply_markup=get_force_join_markup()
                )
                return

            if document.file_size and document.file_size > MAX_FILE_SIZE_BYTES:
                await message.reply_text(messages.FILE_TOO_LARGE)
                return

            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            download_path = await message.download(file_name=os.path.join(DOWNLOAD_DIR, ""))
            try:
                with open(download_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            finally:
                _safe_remove(download_path)

            await _decrypt_and_reply(message, content, document.file_name)
        except Exception:  # noqa: BLE001
            logger.exception("Error handling uploaded file")
            await message.reply_text(messages.GENERIC_ERROR.format(error="Unexpected failure."))

    @bot.on_callback_query(filters.regex("^check_join$"))
    async def callback_check_join(client: Client, callback_query: CallbackQuery) -> None:
        try:
            user_id = callback_query.from_user.id
            if await check_user_joined(client, user_id):
                await callback_query.answer(messages.JOIN_CONFIRMED_ALERT, show_alert=True)
                await callback_query.message.edit_text(messages.JOIN_SUCCESS)
            else:
                await callback_query.answer(messages.JOIN_STILL_MISSING, show_alert=True)
        except Exception:  # noqa: BLE001
            logger.exception("Error in check_join callback")


async def _decrypt_and_reply(message: Message, content: str, filename: str) -> None:
    """Run the decrypt pipeline and send the unlocked `.dark` file back."""
    status_msg = await message.reply_text(messages.PROCESSING_TEXT)
    dark_path = None
    try:
        result = process_dark_config(content)

        base_filename = re.split(r"\.dark", filename, flags=re.IGNORECASE)[0] or "unlocked_config"
        unique_suffix = uuid.uuid4().hex[:8]
        dark_path = os.path.join(DOWNLOAD_DIR, f"{base_filename}_unlocked_{unique_suffix}.dark")

        dark_uri = build_unlocked_dark_uri(result)
        with open(dark_path, "w", encoding="utf-8") as f:
            f.write(dark_uri)

        await status_msg.edit_text(messages.SENDING_TEXT)
        await message.reply_document(document=dark_path, caption=messages.UNLOCK_DONE_CAPTION)
        await status_msg.delete()
    except DarkConfigError as exc:
        # Safe, user-facing message: no internal parser/crypto detail leaks out.
        logger.warning("Dark config processing failed for file=%s: %s", filename, exc)
        await status_msg.edit_text(messages.GENERIC_ERROR.format(error=str(exc)))
    except Exception:  # noqa: BLE001 - unexpected failure, never show raw detail
        logger.exception("Unexpected failure decrypting/unlocking config for file=%s", filename)
        await status_msg.edit_text(
            messages.GENERIC_ERROR.format(error="Something went wrong while processing this file.")
        )
    finally:
        if dark_path:
            _safe_remove(dark_path)


def _safe_remove(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        logger.warning("Could not remove temporary file: %s", path, exc_info=True)
