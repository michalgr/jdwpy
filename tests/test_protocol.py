from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
import asyncio
import pytest
from jdwpy.constants import (
    JdwpErrorCode,
    JdwpEventKind,
    JdwpSuspendPolicy,
    JdwpTypeTag,
)
from jdwpy.spec import (
    IdSizesSpec,
    ObjectID,
    ReferenceTypeID,
    FieldID,
    MethodID,
    Location,
)
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.commands import (
    get_command_class,
    get_response_class,
    register_command,
    VersionCommand,
    VersionResponse,
    IDSizesCommand,
    IDSizesResponse,
    JdwpCommand,
    JdwpResponse,
    SetCommand,
    SetResponse,
    ClearCommand,
    ClearResponse,
    ClearAllBreakpointsCommand,
    ClearAllBreakpointsResponse,
    CountModifier,
    ConditionalModifier,
    ThreadOnlyModifier,
    ClassOnlyModifier,
    ClassMatchModifier,
    ClassExcludeModifier,
    LocationOnlyModifier,
    ExceptionOnlyModifier,
    FieldOnlyModifier,
    StepModifier,
    InstanceOnlyModifier,
    PlatformThreadsOnlyModifier,
)
from jdwpy.connection import (
    JdwpConnection,
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


def create_mock_connection(
    spec: IdSizesSpec | None = None,
) -> tuple[JdwpConnection, asyncio.StreamReader, MockStreamWriter]:
    """Helper factory that constructs all JDWP connection mock objects and starts the loop."""
    reader = asyncio.StreamReader()
    writer = MockStreamWriter()
    sender = JdwpPacketSender(writer)  # type: ignore
    receiver = JdwpPacketReceiver(reader)
    packet_conn = JdwpPacketConnection(sender, receiver)
    packet_conn.start()
    conn = JdwpConnection(packet_conn, spec=spec)
    return conn, reader, writer


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


async def assert_command_roundtrip[T: JdwpResponse | None](
    command: JdwpCommand[T],
    expected_response: T,
    spec: IdSizesSpec | None = None,
) -> None:
    """Generic helper that sets up a mock connection, runs assertions on serialization,

    and executes a full JDWP command-response roundtrip.
    """
    conn, reader, writer = create_mock_connection(spec)
    async with conn:
        # 1. Launch sending the command
        task = asyncio.create_task(conn.send_command(command))
        await asyncio.sleep(0)  # Yield execution to let command write to mock stream

        # 2. Verify command set, command, and command payload match on the wire
        packet = parse_command_packet(writer.buffer)
        assert packet.command_set == command.COMMAND_SET
        assert packet.command == command.COMMAND

        # Deserialize the bytes written to the writer, verifying they reconstruct the command
        deserialized_command = command.__class__.from_bytes(packet.data, conn.spec)
        assert deserialized_command == command

        # 3. If a response is expected, serialize expected_response to feed mock reply
        response_class = get_response_class(command.__class__)
        assert (response_class is None) == (expected_response is None)

        if response_class is not None:
            assert expected_response is not None
            serialized_response = expected_response.to_bytes(conn.spec)
            feed_reply(reader, packet.id, serialized_response)

        response = await task

        # Verify the returned response equals expected_response
        assert response == expected_response

        # Verify dynamic spec updates when IDSizesResponse is received
        if isinstance(response, IDSizesResponse):
            assert conn.spec.field_id_struct.size == response.field_id_size
            assert conn.spec.object_id_struct.size == response.object_id_size
            assert conn.spec.method_id_struct.size == response.method_id_size
            assert (
                conn.spec.reference_type_id_struct.size
                == response.reference_type_id_size
            )
            assert conn.spec.frame_id_struct.size == response.frame_id_size


def test_id_sizes_spec_struct_compilation() -> None:
    """Verifies that IdSizesSpec pre-compiles correct struct sizes and formats."""
    # Test 8-byte spec (typical 64-bit JVM)
    spec_8 = IdSizesSpec.create(
        field_id_size=8,
        method_id_size=8,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    assert spec_8.field_id_struct.format == ">Q"
    assert spec_8.object_id_struct.format == ">Q"
    assert spec_8.field_id_struct.size == 8

    # Test 4-byte spec (typical 32-bit JVM)
    spec_4 = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4,
    )
    assert spec_4.field_id_struct.format == ">I"
    assert spec_4.object_id_struct.format == ">I"
    assert spec_4.field_id_struct.size == 4


def test_jdwp_writer_and_reader_primitives() -> None:
    """Tests big-endian serialization and parsing of primitives."""
    spec = IdSizesSpec.create()
    writer = JdwpWriter(spec)

    writer.write_byte(0xAB)
    writer.write_boolean(True)
    writer.write_boolean(False)
    writer.write_int(0x12345678)
    writer.write_long(0x1122334455667788)
    writer.write_string("Hello JDWP!")

    serialized = writer.get_bytes()
    reader = JdwpReader(serialized, spec)

    assert reader.read_byte() == 0xAB
    assert reader.read_boolean() is True
    assert reader.read_boolean() is False
    assert reader.read_int() == 0x12345678
    assert reader.read_long() == 0x1122334455667788
    assert reader.read_string() == "Hello JDWP!"
    assert reader.remaining == 0


def test_jdwp_writer_and_reader_ids() -> None:
    """Verifies variable length JDWP ID writing and reading."""
    # Test 8-byte mode
    spec_8 = IdSizesSpec.create(object_id_size=8)
    writer_8 = JdwpWriter(spec_8)
    writer_8.write_object_id(ObjectID(0xABCDEF1234567890))

    reader_8 = JdwpReader(writer_8.get_bytes(), spec_8)
    assert reader_8.read_object_id() == 0xABCDEF1234567890

    # Test 4-byte mode
    spec_4 = IdSizesSpec.create(object_id_size=4)
    writer_4 = JdwpWriter(spec_4)
    writer_4.write_object_id(ObjectID(0x76543210))

    reader_4 = JdwpReader(writer_4.get_bytes(), spec_4)
    assert reader_4.read_object_id() == 0x76543210


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
    assert get_command_class(1, 1) is VersionCommand
    assert get_command_class(1, 7) is IDSizesCommand
    assert get_command_class(99, 98) is MockNoResponseCommand
    assert get_command_class(99, 99) is None


@pytest.mark.asyncio
async def test_virtual_machine_command_set() -> None:
    """Verifies flow and serialization for commands in the VirtualMachine Command Set (Set 1)."""
    spec = IdSizesSpec.create()

    # 1. Version Command
    resp_version = VersionResponse(
        description="JVM 14.0",
        jdwp_major=1,
        jdwp_minor=6,
        vm_version="14.0.1",
        vm_name="OpenJDK",
    )
    await assert_command_roundtrip(VersionCommand(), resp_version, spec=spec)

    # 2. IDSizes Command & spec update verification
    resp_ids = IDSizesResponse(
        field_id_size=4,
        method_id_size=4,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    await assert_command_roundtrip(IDSizesCommand(), resp_ids, spec=spec)


@pytest.mark.asyncio
async def test_event_request_command_set() -> None:
    """Verifies flow and serialization for commands in the EventRequest Command Set (Set 15)."""
    # 4-byte JDWP spec configuration
    spec = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4,
    )

    # 1. ClearAllBreakpoints Command
    await assert_command_roundtrip(
        ClearAllBreakpointsCommand(),
        ClearAllBreakpointsResponse(),
        spec=spec,
    )

    # 2. Clear Command
    cmd_clear = ClearCommand(event_kind=JdwpEventKind.BREAKPOINT, request_id=42)
    await assert_command_roundtrip(cmd_clear, ClearResponse(), spec=spec)

    # 3. Set Command with no modifiers
    cmd_set_simple = SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.NONE,
        modifiers=[],
    )
    await assert_command_roundtrip(cmd_set_simple, SetResponse(request_id=100))

    # 4. Set Command with various modifiers
    modifiers = [
        CountModifier(count=5),
        ConditionalModifier(expr_id=123),
        ThreadOnlyModifier(thread=ObjectID(0x11223344)),
        ClassOnlyModifier(clazz=ReferenceTypeID(0x55667788)),
        ClassMatchModifier(class_pattern="java.lang.*"),
        ClassExcludeModifier(class_pattern="sun.*"),
        LocationOnlyModifier(
            loc=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x99AABBCC),
                method_id=MethodID(0xDDEEFF00),
                index=0x1122334455667788,
            )
        ),
        ExceptionOnlyModifier(
            exception_or_null=ReferenceTypeID(0x77889900), caught=True, uncaught=False
        ),
        FieldOnlyModifier(
            declaring=ReferenceTypeID(0x66554433), field=FieldID(0x221100AA)
        ),
        StepModifier(thread=ObjectID(0xDEADBEEF), size=1, depth=2),
        InstanceOnlyModifier(instance=ObjectID(0xFEEDFACE)),
        PlatformThreadsOnlyModifier(),
    ]
    cmd_set_complex = SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.ALL,
        modifiers=modifiers,
    )
    await assert_command_roundtrip(
        cmd_set_complex, SetResponse(request_id=42), spec=spec
    )


@register_command()
@dataclass
class MockNoResponseCommand(JdwpCommand[None]):
    COMMAND_SET: ClassVar[int] = 99
    COMMAND: ClassVar[int] = 98

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@pytest.mark.asyncio
async def test_mock_command_set() -> None:
    """Verifies flow for mock commands without response types."""
    await assert_command_roundtrip(
        MockNoResponseCommand(),
        None,
    )
