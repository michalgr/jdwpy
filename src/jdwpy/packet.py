from __future__ import annotations
import asyncio
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar
from jdwpy.constants import JdwpErrorCode


@dataclass(frozen=True)
class JdwpPacket(ABC):
    """Abstract Base Class representing a raw JDWP Packet."""

    id: int
    flags: int
    data: bytes

    COMMON_HEADER_STRUCT: ClassVar[struct.Struct] = struct.Struct(">IIB")

    def __post_init__(self) -> None:
        expected_reply = bool(self.flags & 0x80)
        is_reply_class = isinstance(self, JdwpReplyPacket)
        if expected_reply != is_reply_class:
            expected_name = "JdwpReplyPacket" if expected_reply else "JdwpCommandPacket"
            actual_name = self.__class__.__name__
            raise ValueError(
                f"Flags 0x80 state mismatch. Got class {actual_name}, "
                f"but flags indicate it should be {expected_name}."
            )

    @property
    def is_reply(self) -> bool:
        """Indicates if the packet is a reply (flags & 0x80)."""
        return bool(self.flags & 0x80)

    @property
    def length(self) -> int:
        """Total length of the packet (including header)."""
        return 11 + len(self.data)

    @abstractmethod
    def serialize(self, writer: asyncio.StreamWriter) -> None:
        """Serializes the packet and writes it to the buffered stream writer."""
        pass

    @classmethod
    async def deserialize(cls, reader: asyncio.StreamReader) -> JdwpPacket:
        """Asynchronously reads and deserializes a complete JDWP packet from the stream reader."""
        header = await reader.readexactly(11)
        length, _, flags = cls.COMMON_HEADER_STRUCT.unpack(header[:9])

        if length < 11:
            raise ValueError(f"Invalid JDWP packet length: {length} (must be >= 11)")

        data = await reader.readexactly(length - 11)

        if flags & 0x80:
            return JdwpReplyPacket.parse(header, data)
        else:
            return JdwpCommandPacket.parse(header, data)


@dataclass(frozen=True)
class JdwpCommandPacket(JdwpPacket):
    """Represents a JDWP Command Packet."""

    command_set: int
    command: int

    HEADER_STRUCT: ClassVar[struct.Struct] = struct.Struct(">IIBBB")

    def serialize(self, writer: asyncio.StreamWriter) -> None:
        header = self.HEADER_STRUCT.pack(
            self.length, self.id, self.flags, self.command_set, self.command
        )
        writer.write(header + self.data)

    @classmethod
    def parse(cls, header: bytes, data: bytes) -> JdwpCommandPacket:
        """Parses a command packet from pre-read header and data bytes."""
        _, packet_id, flags, command_set, command = cls.HEADER_STRUCT.unpack(header)
        return cls(
            id=packet_id,
            flags=flags,
            command_set=command_set,
            command=command,
            data=data,
        )


@dataclass(frozen=True)
class JdwpReplyPacket(JdwpPacket):
    """Represents a JDWP Reply Packet."""

    error_code: JdwpErrorCode

    HEADER_STRUCT: ClassVar[struct.Struct] = struct.Struct(">IIBH")

    def serialize(self, writer: asyncio.StreamWriter) -> None:
        header = self.HEADER_STRUCT.pack(
            self.length, self.id, self.flags, self.error_code
        )
        writer.write(header + self.data)

    @classmethod
    def parse(cls, header: bytes, data: bytes) -> JdwpReplyPacket:
        """Parses a reply packet from pre-read header and data bytes."""
        _, packet_id, flags, error_code = cls.HEADER_STRUCT.unpack(header)
        try:
            err = JdwpErrorCode(error_code)
        except ValueError:
            err = error_code  # type: ignore
        return cls(id=packet_id, flags=flags, error_code=err, data=data)
