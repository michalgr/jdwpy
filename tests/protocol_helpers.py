from __future__ import annotations
import asyncio
from jdwpy.spec import IdSizesSpec
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.constants import JdwpErrorCode
from jdwpy import commands
from jdwpy.connection import (
    SimpleJdwpConnection,
    JdwpConnectionWithAsyncLoop,
    JdwpPacketConnection,
    JdwpPacketSender,
    JdwpPacketReceiver,
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


class MockJdwpPacketSender(JdwpPacketSender):
    """Mock JdwpPacketSender that writes packets to an asyncio.Queue."""

    sent_packets: asyncio.Queue[JdwpPacket]
    closed: bool

    def __init__(self) -> None:
        self.sent_packets = asyncio.Queue()
        self.closed = False

    async def send(self, packet: JdwpPacket) -> None:
        if self.closed:
            raise RuntimeError("Sender is closed")
        await self.sent_packets.put(packet)

    async def close(self) -> None:
        self.closed = True


class MockJdwpPacketReceiver(JdwpPacketReceiver):
    """Mock JdwpPacketReceiver that reads packets from an asyncio.Queue."""

    incoming_packets: asyncio.Queue[JdwpPacket]
    closed: bool
    _error_to_raise: BaseException | None

    def __init__(self) -> None:
        self.incoming_packets = asyncio.Queue()
        self.closed = False
        self._error_to_raise = None

    def inject_error(self, error: BaseException) -> None:
        """Injects an error into the receiver, making any subsequent receive fail."""
        self._error_to_raise = error
        self.incoming_packets.shutdown()

    async def receive(self) -> JdwpPacket:
        if self._error_to_raise:
            raise self._error_to_raise
        if self.closed:
            raise RuntimeError("Receiver is closed")
        try:
            return await self.incoming_packets.get()
        except asyncio.QueueShutDown:
            if self._error_to_raise:
                raise self._error_to_raise
            raise RuntimeError("Receiver is closed")

    async def close(self) -> None:
        self.closed = True
        self.incoming_packets.shutdown()


def create_mock_session(
    spec: IdSizesSpec | None = None,
) -> tuple[JdwpConnectionWithAsyncLoop, MockJdwpPacketReceiver, MockJdwpPacketSender]:
    """Helper factory that constructs all JDWP session mock objects."""
    sender = MockJdwpPacketSender()
    receiver = MockJdwpPacketReceiver()
    packet_conn = JdwpPacketConnection(sender, receiver)
    conn = SimpleJdwpConnection(packet_conn, spec=spec)
    session = JdwpConnectionWithAsyncLoop(conn)
    session.start()
    return session, receiver, sender


async def assert_command_roundtrip[T: commands.JdwpResponse | None](
    command: commands.JdwpCommand[T],
    expected_response: T,
    spec: IdSizesSpec | None = None,
) -> None:
    """Generic helper that sets up a mock connection, runs assertions on serialization,
    and executes a full JDWP command-response roundtrip.
    """
    session, receiver, sender = create_mock_session(spec)
    async with session:
        # 1. Launch sending the command
        task = asyncio.create_task(session.send_command(command))

        # 2. Retrieve sent packet and verify command set, command, and command payload
        packet = await sender.sent_packets.get()
        assert isinstance(packet, JdwpCommandPacket)
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
            reply = JdwpReplyPacket(
                id=packet.id,
                flags=0x80,
                error_code=JdwpErrorCode.NONE,
                data=serialized_response,
            )
            await receiver.incoming_packets.put(reply)

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
