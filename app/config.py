"""Centralized configuration loaded from environment variables.

No secret ever lives in source code. All values are read at import time and
validated immediately so the bot fails fast (with a clear message) instead of
crashing later with a confusing traceback.
"""

from __future__ import annotations

import logging
import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is optional at runtime
    pass

logger = logging.getLogger(__name__)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _require_int(name: str) -> int:
    raw = os.getenv(name)
    if not raw:
        raise ConfigError(f"Missing required environment variable: {name}")
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name} must be an integer") from exc


def _require_str(name: str) -> str:
    raw = os.getenv(name)
    if not raw:
        raise ConfigError(f"Missing required environment variable: {name}")
    return raw.strip()


def _optional_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


# ==================== Telegram / Pyrogram credentials ====================
API_ID: int = _require_int("API_ID")
API_HASH: str = _require_str("API_HASH")
BOT_TOKEN: str = _require_str("BOT_TOKEN")

# ==================== Force-join channel ====================
CHANNEL_USERNAME: str = _optional_str("CHANNEL_USERNAME", "minarulsensi")
CHANNEL_URL: str = _optional_str("CHANNEL_URL", f"https://t.me/{CHANNEL_USERNAME}")

# ==================== Runtime behaviour ====================
LOG_LEVEL: str = _optional_str("LOG_LEVEL", "INFO")
SESSION_NAME: str = _optional_str("SESSION_NAME", "dark_decryptor_bot")
DOWNLOAD_DIR: str = _optional_str("DOWNLOAD_DIR", "downloads")
MAX_FILE_SIZE_MB: int = int(_optional_str("MAX_FILE_SIZE_MB", "5"))

# ==================== Fixed cryptographic material ====================
# These are protocol constants used by the Dark Tunnel export format itself
# (not secrets belonging to this bot's operator), so they stay as constants.
OUTER_KEY: bytes = b"$B&E)H@McQfThWmZq4t7w!z%C*F-JaNd"
INNER_KEY: bytes = b"F)J@NcRfUjXn2r4u7x!A%D*G"
IV: bytes = bytes.fromhex("232e39185523184a5723586242200e05")


def configure_logging() -> None:
    """Set up structured logging for the whole process."""
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Pyrogram is noisy at INFO; keep it at WARNING unless DEBUG is requested.
    if level > logging.DEBUG:
        logging.getLogger("pyrogram").setLevel(logging.WARNING)


def validate() -> None:
    """Run all validation eagerly; call once at process startup."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    logger.info("Configuration loaded successfully (channel=@%s)", CHANNEL_USERNAME)
