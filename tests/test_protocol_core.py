from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from typing import ClassVar, Self
import pytest
from jdwpy.spec import IdSizesSpec
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy import commands, JdwpException
from jdwpy.constants import JdwpErrorCode

from tests.protocol_helpers import (
    MockStreamWriter,
    create_mock_session,
    assert_command_roundtrip,
)


@commands.register_command()
@dataclass
class MockNoResponseCommand(commands.JdwpCommand[None]):
    COMMAND_SET: ClassVar[int] = 99
    COMMAND: ClassVar[int] = 98

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@pytest.mark.asyncio
async def test_packet_stream_serialization() -> None:
    """Verifies async stream-based serialization and deserialization of JdwpPackets."""
    # 1. Test Command Packet
    cmd_payload = b"\x00\x00\x00\x05Hello"
    cmd_packet = JdwpCommandPacket(
        id=42, flags=0x00, command_set=1, command=7, data=cmd_payload
    )

    writer = MockStreamWriter()
    cmd_packet.serialize(writer)  # type: ignore

    # Read back from stream reader
    reader = asyncio.StreamReader()
    reader.feed_data(writer.buffer)
    reader.feed_eof()

    deserialized = await JdwpPacket.deserialize(reader)
    assert isinstance(deserialized, JdwpCommandPacket)
    assert deserialized.id == 42
    assert deserialized.flags == 0x00
    assert deserialized.command_set == 1
    assert deserialized.command == 7
    assert deserialized.data == cmd_payload
    assert deserialized.is_reply is False

    # 2. Test Reply Packet
    reply_payload = b"World!"
    reply_packet = JdwpReplyPacket(
        id=42, flags=0x80, error_code=JdwpErrorCode.INVALID_OBJECT, data=reply_payload
    )

    writer_reply = MockStreamWriter()
    reply_packet.serialize(writer_reply)  # type: ignore

    reader_reply = asyncio.StreamReader()
    reader_reply.feed_data(writer_reply.buffer)
    reader_reply.feed_eof()

    deserialized_reply = await JdwpPacket.deserialize(reader_reply)
    assert isinstance(deserialized_reply, JdwpReplyPacket)
    assert deserialized_reply.id == 42
    assert deserialized_reply.flags == 0x80
    assert deserialized_reply.error_code == JdwpErrorCode.INVALID_OBJECT
    assert deserialized_reply.data == reply_payload
    assert deserialized_reply.is_reply is True


def test_command_registry_indexing() -> None:
    """Verifies that concrete commands are successfully indexed in the registry."""
    assert commands.get_command_class(1, 1) is commands.vm.VersionCommand
    assert commands.get_command_class(1, 7) is commands.vm.IDSizesCommand
    assert commands.get_command_class(99, 98) is MockNoResponseCommand
    assert commands.get_command_class(99, 99) is None


@pytest.mark.asyncio
async def test_mock_command_set() -> None:
    """Verifies flow for mock commands without response types."""
    await assert_command_roundtrip(
        MockNoResponseCommand(),
        None,
    )


@pytest.mark.asyncio
async def test_unexpected_error_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Verifies that receiving a JDWP error not listed in the command's ALLOWED_ERRORS logs a warning."""
    spec = IdSizesSpec.create()
    session, receiver, sender = create_mock_session(spec)

    async with session:
        # Launch VersionCommand which only allows VM_DEAD and NONE
        task = asyncio.create_task(session.send_command(commands.vm.VersionCommand()))

        # Get command packet to retrieve ID
        packet = await sender.sent_packets.get()

        # Feed an invalid reply with an unexpected error: INVALID_THREAD (10)
        reply = JdwpReplyPacket(
            id=packet.id,
            flags=0x80,
            error_code=JdwpErrorCode.INVALID_THREAD,
            data=b"",
        )
        await receiver.incoming_packets.put(reply)

        # Assert that executing the task raises JdwpException
        with pytest.raises(JdwpException) as exc_info:
            await task

        assert exc_info.value.error_code == JdwpErrorCode.INVALID_THREAD
        assert exc_info.value.raw_error_code == JdwpErrorCode.INVALID_THREAD.value
        assert isinstance(exc_info.value.command, commands.vm.VersionCommand)
        assert "failed with error: INVALID_THREAD" in str(exc_info.value)

        # Assert that a warning was captured in log
        warnings = [
            rec
            for rec in caplog.records
            if rec.levelno == logging.WARNING
            and "Received unexpected JDWP error code INVALID_THREAD" in rec.message
        ]
        assert len(warnings) == 1


@pytest.mark.asyncio
async def test_close_with_pending_command() -> None:
    spec = IdSizesSpec.create()
    session, receiver, sender = create_mock_session(spec)

    async with session:
        # Send a command but don't feed a response
        task = asyncio.create_task(session.send_command(commands.vm.VersionCommand()))
        await sender.sent_packets.get()

    # After exiting the context manager (which calls close()), the task should be resolved/failed, not hang!
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=1.0)


@pytest.mark.asyncio
async def test_send_command_on_closed_connection() -> None:
    spec = IdSizesSpec.create()
    session, receiver, sender = create_mock_session(spec)

    async with session:
        pass  # Just establish and close immediately

    # Now the connection is closed. Sending a command should raise RuntimeError.
    with pytest.raises(RuntimeError, match="Connection closed"):
        await session.send_command(commands.vm.VersionCommand())


@pytest.mark.asyncio
async def test_send_command_on_errored_connection() -> None:
    spec = IdSizesSpec.create()
    session, receiver, sender = create_mock_session(spec)

    async with session:
        # Feed an error to the receiver that will crash the read loop
        receiver.inject_error(ValueError("Mock connection error"))
        await asyncio.sleep(0.01)  # Let read loop wake up and crash

        # Now the connection is in error. Sending a command should raise RuntimeError.
        with pytest.raises(RuntimeError, match="Connection closed due to error"):
            await session.send_command(commands.vm.VersionCommand())
