from __future__ import annotations
import asyncio
from jdwpy.spec import IdSizesSpec
from jdwpy.packet import JdwpCommandPacket, JdwpReplyPacket
from jdwpy.constants import JdwpErrorCode
from jdwpy import commands
from jdwpy.connection import (
    DefaultJdwpConnection,
    JdwpConnectionWithAsyncLoop,
    JdwpPacketConnection,
    StreamJdwpPacketSender,
    StreamJdwpPacketReceiver,
)


class MockStreamWriter:
    """Mock StreamWriter for testing connections completely in-memory."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        await asyncio.sleep(0)  # Yield execution

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        await asyncio.sleep(0)


def create_mock_session(
    spec: IdSizesSpec | None = None,
) -> tuple[JdwpConnectionWithAsyncLoop, asyncio.StreamReader, MockStreamWriter]:
    """Helper factory that constructs all JDWP session mock objects."""
    reader = asyncio.StreamReader()
    writer = MockStreamWriter()
    sender = StreamJdwpPacketSender(writer)  # type: ignore
    receiver = StreamJdwpPacketReceiver(reader)
    packet_conn = JdwpPacketConnection(sender, receiver)
    conn = DefaultJdwpConnection(packet_conn, spec=spec)
    session = JdwpConnectionWithAsyncLoop(conn)
    session.start()
    return session, reader, writer


def parse_command_packet(buffer: bytes | bytearray) -> JdwpCommandPacket:
    """Parses a JdwpCommandPacket from a raw bytes buffer."""
    if len(buffer) < 11:
        raise ValueError("Buffer too short for JDWP packet")
    return JdwpCommandPacket.from_bytes(bytes(buffer[:11]), bytes(buffer[11:]))


def feed_reply(reader: asyncio.StreamReader, packet_id: int, payload: bytes) -> None:
    """Serializes a successful JdwpReplyPacket and feeds it to the StreamReader."""
    reply = JdwpReplyPacket(
        id=packet_id,
        flags=0x80,
        error_code=JdwpErrorCode.NONE,
        data=payload,
    )
    reader.feed_data(reply.to_bytes())


async def assert_command_roundtrip[T: commands.JdwpResponse | None](
    command: commands.JdwpCommand[T],
    expected_response: T,
    spec: IdSizesSpec | None = None,
) -> None:
    """Generic helper that sets up a mock connection, runs assertions on serialization,
    and executes a full JDWP command-response roundtrip.
    """
    session, reader, writer = create_mock_session(spec)
    async with session:
        # 1. Launch sending the command
        task = asyncio.create_task(session.send_command(command))
        await asyncio.sleep(0)  # Yield execution to let command write to mock stream

        # 2. Verify command set, command, and command payload match on the wire
        packet = parse_command_packet(writer.buffer)
        assert packet.command_set == command.COMMAND_SET
        assert packet.command == command.COMMAND

        # Deserialize the bytes written to the writer, verifying they reconstruct the command
        deserialized_command = command.__class__.from_bytes(
            packet.data, session.delegate.spec
        )
        assert deserialized_command == command

        # 3. If a response is expected, serialize expected_response to feed mock reply
        response_class = commands.get_response_class(command.__class__)
        assert (response_class is None) == (expected_response is None)

        if response_class is not None:
            assert expected_response is not None
            serialized_response = expected_response.to_bytes(session.delegate.spec)
            feed_reply(reader, packet.id, serialized_response)

        response = await task

        # Verify the returned response equals expected_response
        assert response == expected_response

        # Verify dynamic spec updates when commands.vm.IDSizesResponse is received
        if isinstance(response, commands.vm.IDSizesResponse):
            assert session.delegate.spec.field_id_struct.size == response.field_id_size
            assert (
                session.delegate.spec.object_id_struct.size == response.object_id_size
            )
            assert (
                session.delegate.spec.method_id_struct.size == response.method_id_size
            )
            assert (
                session.delegate.spec.reference_type_id_struct.size
                == response.reference_type_id_size
            )
            assert session.delegate.spec.frame_id_struct.size == response.frame_id_size
