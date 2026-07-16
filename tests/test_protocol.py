from __future__ import annotations
from typing import ClassVar
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
    register_command,
    VersionCommand,
    VersionResponse,
    IDSizesCommand,
    IDSizesResponse,
    JdwpCommand,
    SetCommand,
    SetResponse,
    ClearCommand,
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


def create_mock_connection() -> tuple[
    JdwpConnection, asyncio.StreamReader, MockStreamWriter
]:
    """Helper factory that constructs all JDWP connection mock objects and starts the loop."""
    reader = asyncio.StreamReader()
    writer = MockStreamWriter()
    sender = JdwpPacketSender(writer)  # type: ignore
    receiver = JdwpPacketReceiver(reader)
    packet_conn = JdwpPacketConnection(sender, receiver)
    packet_conn.start()
    conn = JdwpConnection(packet_conn)
    return conn, reader, writer


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


def test_concrete_commands_payloads() -> None:
    """Verifies serialization and deserialization of command and reply payloads."""
    spec = IdSizesSpec.create()

    # 1. Version Command Set
    cmd = VersionCommand()
    assert cmd.to_bytes(spec) == b""  # Empty payload request

    resp = VersionResponse(
        description="JVM 14.0",
        jdwp_major=1,
        jdwp_minor=6,
        vm_version="14.0.1",
        vm_name="OpenJDK",
    )
    deserialized_resp = VersionResponse.from_bytes(resp.to_bytes(spec), spec)
    assert deserialized_resp.description == "JVM 14.0"
    assert deserialized_resp.jdwp_major == 1
    assert deserialized_resp.jdwp_minor == 6
    assert deserialized_resp.vm_version == "14.0.1"
    assert deserialized_resp.vm_name == "OpenJDK"

    # 2. IDSizes Command Set
    resp_ids = IDSizesResponse(
        field_id_size=4,
        method_id_size=4,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    deserialized_ids = IDSizesResponse.from_bytes(resp_ids.to_bytes(spec), spec)
    assert deserialized_ids.field_id_size == 4
    assert deserialized_ids.method_id_size == 4
    assert deserialized_ids.object_id_size == 8
    assert deserialized_ids.reference_type_id_size == 8
    assert deserialized_ids.frame_id_size == 8


@pytest.mark.asyncio
async def test_jdwp_connection_full_flow() -> None:
    """Tests the JDWP handshake, background loop, futures routing, and dynamic spec replacement."""
    conn, reader, writer = create_mock_connection()

    # 2. Send IDSizesCommand and intercept raw writer bytes to feed mock response
    task = asyncio.create_task(conn.send_command(IDSizesCommand()))

    # Let the event loop run to send command
    await asyncio.sleep(0)

    # Verify command was sent
    assert len(writer.buffer) >= 11
    packet = JdwpCommandPacket.from_bytes(writer.buffer[:11], writer.buffer[11:])
    assert packet.id == 1
    assert packet.command_set == 1
    assert packet.command == 7
    writer.buffer.clear()

    # Construct and feed the mock IDSizes response packet using library components
    resp_ids = IDSizesResponse(
        field_id_size=4,
        method_id_size=4,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    payload = resp_ids.to_bytes(conn.spec)

    reply_packet = JdwpReplyPacket(
        id=packet.id,
        flags=0x80,
        error_code=JdwpErrorCode.NONE,
        data=payload,
    )
    temp_writer = MockStreamWriter()
    reply_packet.serialize(temp_writer)  # type: ignore
    reader.feed_data(temp_writer.buffer)

    # Wait for command response
    response = await task
    assert isinstance(response, IDSizesResponse)
    assert response.field_id_size == 4
    assert response.method_id_size == 4
    assert response.object_id_size == 8

    # Verify Dynamic IDSizes Spec Replacement!
    assert conn.spec.field_id_struct.size == 4
    assert conn.spec.object_id_struct.size == 8

    await conn.close()


def test_event_request_commands_serialization() -> None:
    spec = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4,
    )

    # 1. ClearAllBreakpoints
    cmd_clear_all = ClearAllBreakpointsCommand()
    assert cmd_clear_all.to_bytes(spec) == b""
    resp_clear_all = ClearAllBreakpointsResponse()
    assert resp_clear_all.to_bytes(spec) == b""

    # 2. Clear
    cmd_clear = ClearCommand(event_kind=JdwpEventKind.BREAKPOINT, request_id=42)
    serialized_clear = cmd_clear.to_bytes(spec)
    assert serialized_clear == b"\x02\x00\x00\x00\x2a"
    deserialized_clear = ClearCommand.from_bytes(serialized_clear, spec)
    assert deserialized_clear.event_kind == JdwpEventKind.BREAKPOINT
    assert deserialized_clear.request_id == 42

    # 3. Set with various modifiers
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

    cmd_set = SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.ALL,
        modifiers=modifiers,
    )

    serialized_set = cmd_set.to_bytes(spec)
    deserialized_set = SetCommand.from_bytes(serialized_set, spec)

    assert deserialized_set.event_kind == JdwpEventKind.BREAKPOINT
    assert deserialized_set.suspend_policy == JdwpSuspendPolicy.ALL
    assert len(deserialized_set.modifiers) == len(modifiers)

    # Validate each modifier
    assert isinstance(deserialized_set.modifiers[0], CountModifier)
    assert deserialized_set.modifiers[0].count == 5

    assert isinstance(deserialized_set.modifiers[1], ConditionalModifier)
    assert deserialized_set.modifiers[1].expr_id == 123

    assert isinstance(deserialized_set.modifiers[2], ThreadOnlyModifier)
    assert deserialized_set.modifiers[2].thread == 0x11223344

    assert isinstance(deserialized_set.modifiers[3], ClassOnlyModifier)
    assert deserialized_set.modifiers[3].clazz == 0x55667788

    assert isinstance(deserialized_set.modifiers[4], ClassMatchModifier)
    assert deserialized_set.modifiers[4].class_pattern == "java.lang.*"

    assert isinstance(deserialized_set.modifiers[5], ClassExcludeModifier)
    assert deserialized_set.modifiers[5].class_pattern == "sun.*"

    assert isinstance(deserialized_set.modifiers[6], LocationOnlyModifier)
    loc = deserialized_set.modifiers[6].loc
    assert loc.type_tag == JdwpTypeTag.CLASS
    assert loc.class_id == 0x99AABBCC
    assert loc.method_id == 0xDDEEFF00
    assert loc.index == 0x1122334455667788

    assert isinstance(deserialized_set.modifiers[7], ExceptionOnlyModifier)
    assert deserialized_set.modifiers[7].exception_or_null == 0x77889900
    assert deserialized_set.modifiers[7].caught is True
    assert deserialized_set.modifiers[7].uncaught is False

    assert isinstance(deserialized_set.modifiers[8], FieldOnlyModifier)
    assert deserialized_set.modifiers[8].declaring == 0x66554433
    assert deserialized_set.modifiers[8].field == 0x221100AA

    assert isinstance(deserialized_set.modifiers[9], StepModifier)
    assert deserialized_set.modifiers[9].thread == 0xDEADBEEF
    assert deserialized_set.modifiers[9].size == 1
    assert deserialized_set.modifiers[9].depth == 2

    assert isinstance(deserialized_set.modifiers[10], InstanceOnlyModifier)
    assert deserialized_set.modifiers[10].instance == 0xFEEDFACE

    assert isinstance(deserialized_set.modifiers[11], PlatformThreadsOnlyModifier)


@pytest.mark.asyncio
async def test_event_request_connection_flow() -> None:
    conn, reader, writer = create_mock_connection()

    task = asyncio.create_task(conn.send_command(ClearAllBreakpointsCommand()))
    await asyncio.sleep(0)

    assert len(writer.buffer) == 11
    packet = JdwpCommandPacket.from_bytes(writer.buffer, b"")
    assert packet.command_set == 15
    assert packet.command == 3
    writer.buffer.clear()

    reply_packet = JdwpReplyPacket(
        id=packet.id,
        flags=0x80,
        error_code=JdwpErrorCode.NONE,
        data=b"",
    )
    temp_writer = MockStreamWriter()
    reply_packet.serialize(temp_writer)  # type: ignore
    reader.feed_data(temp_writer.buffer)

    response = await task
    assert isinstance(response, ClearAllBreakpointsResponse)

    await conn.close()


@pytest.mark.asyncio
async def test_event_request_set_connection_flow() -> None:
    conn, reader, writer = create_mock_connection()

    cmd = SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.NONE,
        modifiers=[],
    )
    task = asyncio.create_task(conn.send_command(cmd))
    await asyncio.sleep(0)

    assert len(writer.buffer) >= 11
    packet = JdwpCommandPacket.from_bytes(writer.buffer[:11], writer.buffer[11:])
    assert packet.command_set == 15
    assert packet.command == 1
    writer.buffer.clear()

    resp = SetResponse(request_id=100)
    reply_packet = JdwpReplyPacket(
        id=packet.id,
        flags=0x80,
        error_code=JdwpErrorCode.NONE,
        data=resp.to_bytes(conn.spec),
    )
    temp_writer = MockStreamWriter()
    reply_packet.serialize(temp_writer)  # type: ignore
    reader.feed_data(temp_writer.buffer)

    response = await task
    assert isinstance(response, SetResponse)
    assert response.request_id == 100

    await conn.close()


@register_command()
class MockNoResponseCommand(JdwpCommand[None]):
    COMMAND_SET: ClassVar[int] = 99
    COMMAND: ClassVar[int] = 98

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> MockNoResponseCommand:
        return cls()


@pytest.mark.asyncio
async def test_jdwp_command_no_response() -> None:
    conn, reader, writer = create_mock_connection()

    res = await conn.send_command(MockNoResponseCommand())
    assert res is None

    assert len(writer.buffer) == 11
    packet = JdwpCommandPacket.from_bytes(writer.buffer, b"")
    assert packet.command_set == 99
    assert packet.command == 98

    await conn.close()
