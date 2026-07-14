"""Minimal MessagePack decoder used by the Dark Tunnel export format.

Kept dependency-free (no `msgpack` package required) since the original
implementation only needs a decoder for a handful of MessagePack markers.
"""

from __future__ import annotations

from struct import unpack
from typing import Any


class MsgpackDecodeError(ValueError):
    """Raised when the input bytes are not valid/complete MessagePack data."""


class MsgpackReader:
    """Streaming reader that decodes a MessagePack-encoded byte buffer."""

    __slots__ = ("data", "pos")

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def read(self, size: int) -> bytes:
        end = self.pos + size
        if end > len(self.data):
            raise MsgpackDecodeError("truncated msgpack data")
        chunk = self.data[self.pos : end]
        self.pos = end
        return chunk

    def read_u8(self) -> int:
        return self.read(1)[0]

    def read_str(self, size: int) -> str:
        return self.read(size).decode("utf-8")

    def read_map(self, size: int) -> dict[Any, Any]:
        return {self.unpack(): self.unpack() for _ in range(size)}

    def read_array(self, size: int) -> list[Any]:
        return [self.unpack() for _ in range(size)]

    def unpack(self) -> Any:  # noqa: C901 - inherent branching of a binary format
        code = self.read_u8()
        if code <= 0x7F:
            return code
        if code >= 0xE0:
            return code - 0x100
        if 0x80 <= code <= 0x8F:
            return self.read_map(code & 0x0F)
        if 0x90 <= code <= 0x9F:
            return self.read_array(code & 0x0F)
        if 0xA0 <= code <= 0xBF:
            return self.read_str(code & 0x1F)
        if code == 0xC0:
            return None
        if code == 0xC2:
            return False
        if code == 0xC3:
            return True
        if code == 0xC4:
            return self.read(self.read_u8())
        if code == 0xC5:
            return self.read(unpack(">H", self.read(2))[0])
        if code == 0xC6:
            return self.read(unpack(">I", self.read(4))[0])
        if code == 0xCA:
            return unpack(">f", self.read(4))[0]
        if code == 0xCB:
            return unpack(">d", self.read(8))[0]
        if code == 0xCC:
            return self.read_u8()
        if code == 0xCD:
            return unpack(">H", self.read(2))[0]
        if code == 0xCE:
            return unpack(">I", self.read(4))[0]
        if code == 0xCF:
            return unpack(">Q", self.read(8))[0]
        if code == 0xD0:
            return unpack(">b", self.read(1))[0]
        if code == 0xD1:
            return unpack(">h", self.read(2))[0]
        if code == 0xD2:
            return unpack(">i", self.read(4))[0]
        if code == 0xD3:
            return unpack(">q", self.read(8))[0]
        if code == 0xD9:
            return self.read_str(self.read_u8())
        if code == 0xDA:
            return self.read_str(unpack(">H", self.read(2))[0])
        if code == 0xDB:
            return self.read_str(unpack(">I", self.read(4))[0])
        if code == 0xDC:
            return self.read_array(unpack(">H", self.read(2))[0])
        if code == 0xDD:
            return self.read_array(unpack(">I", self.read(4))[0])
        if code == 0xDE:
            return self.read_map(unpack(">H", self.read(2))[0])
        if code == 0xDF:
            return self.read_map(unpack(">I", self.read(4))[0])
        raise MsgpackDecodeError(f"unsupported msgpack marker 0x{code:02x}")


def msgpack_unpack(data: bytes) -> Any:
    """Decode a full MessagePack buffer, raising if trailing bytes remain."""
    reader = MsgpackReader(data)
    value = reader.unpack()
    if reader.pos != len(data):
        raise MsgpackDecodeError(f"msgpack has {len(data) - reader.pos} trailing bytes")
    return value
