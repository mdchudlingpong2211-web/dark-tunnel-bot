"""Low-level cryptographic and encoding helpers for the Dark Tunnel format."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

try:
    from cryptography.hazmat.decrepit.ciphers import modes
except ImportError:  # older `cryptography` versions keep CFB in the main module
    from cryptography.hazmat.primitives.ciphers import modes

from app.config import IV


def b64decode_any(value: str) -> bytes:
    """Decode base64 that may be URL-safe, standard, or missing padding."""
    value = value.strip().replace("%2B", "+").replace("%2F", "/").replace("%3D", "=")
    value += "=" * ((4 - len(value) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(value)
    except (ValueError, TypeError):
        return base64.b64decode(value)


def aes_cfb_decrypt(data: bytes, key: bytes) -> bytes:
    """Decrypt AES-CFB ciphertext using the shared static IV."""
    return Cipher(algorithms.AES(key), modes.CFB(IV)).decryptor().update(data)
